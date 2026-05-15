"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py

Institutional-grade market regime detection for XAUUSD.
Uses statistical price features and Gaussian Mixture Models (GMM) to classify
market states into categories such as Trending, Ranging, and News Shock.

Usage:
    detector = RegimeDetector()
    # For real-time detection
    regime_info = detector.detect(ohlcv_df)

    # For historical labeling
    df_with_regimes = detector.label_history(large_df)

Regime data structures are immutable (frozen) and enforce strict confidence
and transition score validation to ensure technical trust in market analysis.

Author : triqbit (Institutional Research Suite)
License: MIT
"""

from __future__ import annotations

import contextlib
import os
import stat
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import structlog
from pydantic import BaseModel, ConfigDict, Field
from scipy import stats
from sklearn.mixture import GaussianMixture

from src.core.constants import MarketRegime
from src.core.schemas import RegimeInfo

logger = structlog.get_logger(__name__)


class RegimeAnalysisReport(BaseModel):
    """
    Comprehensive historical market regime analysis report.
    """

    timestamp: str = Field(..., description="Time of report generation")
    counts_pct: dict[str, float] = Field(..., description="Percentage frequency of each regime")
    avg_durations: dict[str, float] = Field(
        ..., description="Average duration of each regime in bars"
    )
    transitions: pd.DataFrame = Field(..., description="Regime transition matrix")
    summary_text: str = Field(..., description="Narrative summary of the analysis")
    regime_list: list[Any] = Field(
        default_factory=list, description="Detailed list of regime metrics"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_report_section(self) -> Any:
        """
        Convert report to RegimeSection for ResearchReporter.
        """
        from src.research.reporting import RegimeSection

        # Stability is the mean of all average durations
        stability = (
            sum(self.avg_durations.values()) / len(self.avg_durations)
            if self.avg_durations
            else 0.0
        )

        # Transition insights
        top_transitions = []
        for reg in self.transitions.index:
            if reg == MarketRegime.UNKNOWN.value:
                continue
            # Get most likely transition that is NOT to itself
            other_regs = self.transitions.columns[self.transitions.columns != reg]
            if not other_regs.empty:
                valid_targets = [t for t in other_regs if t != MarketRegime.UNKNOWN.value]
                if valid_targets:
                    target = self.transitions.loc[reg, valid_targets].idxmax()
                    prob = self.transitions.loc[reg, target]
                    if prob > 0.05:
                        top_transitions.append(f"{reg} -> {target} ({prob:.1%})")

        transition_txt = " | ".join(top_transitions[:3])
        if not transition_txt:
            transition_txt = "No significant transitions detected."

        return RegimeSection(
            summary=self.summary_text,
            regimes=self.regime_list,
            transition_insights=f"Stability: {stability:.1f} bars. Common paths: {transition_txt}",
        )


class RegimeDetector:
    """
    Detects market regimes using statistical price features.
    Optimized for XAUUSD M5/M15 timeframes.
    """

    # Scaling factor for trend angle calculation (normalized slope -> degrees)
    ANGLE_SCALE: float = 1000.0

    # Institutional standard feature set
    FEATURE_COLUMNS: list[str] = [
        "atr_ratio",
        "efficiency_ratio",
        "slope",
        "z_score",
        "kurtosis",
        "skewness",
        "vol_of_vol",
        "vol_clustering",
    ]

    # Heuristic Thresholds (Institutional Standard)
    THRESH_NEWS_SHOCK_ATR: float = 2.0
    THRESH_NEWS_SHOCK_ER: float = 0.7
    THRESH_NEWS_SHOCK_VOV: float = 1.2

    THRESH_BREAKOUT_ATR: float = 1.25
    THRESH_BREAKOUT_ER: float = 0.5

    THRESH_TRENDING_ER: float = 0.4
    THRESH_TRENDING_ANGLE: float = 15.0

    THRESH_MEAN_REV_Z: float = 1.8
    THRESH_MEAN_REV_ER: float = 0.35

    THRESH_DRIFT_ATR: float = 1.1
    THRESH_DRIFT_ANGLE: float = 2.0
    THRESH_DRIFT_VOV: float = 1.3

    def __init__(self, window: int = 20, long_window: int = 100) -> None:
        self.window = window
        self.long_window = long_window
        self._last_regime: MarketRegime = MarketRegime.UNKNOWN
        self._gmm: GaussianMixture | None = None
        self._cluster_to_regime: dict[int, MarketRegime] = {}
        self.transition_matrix: pd.DataFrame | None = None

    def _calculate_efficiency_ratio(self, prices: np.ndarray) -> float:
        """Kaufman Efficiency Ratio: net change / sum of absolute changes."""
        if len(prices) < 2:
            return 0.5
        net_change = abs(prices[-1] - prices[0])
        abs_changes = np.abs(np.diff(prices))
        sum_abs_changes = np.sum(abs_changes)
        if sum_abs_changes < 1e-9:
            return 0.5
        return float(net_change / (sum_abs_changes + 1e-9))

    def _calculate_slope(self, prices: np.ndarray) -> float:
        """Normalized linear regression slope."""
        n = len(prices)
        if n < 2:
            return 0.0
        x = np.arange(n)
        y = prices
        # Standardize x to center it, improves numerical stability
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        denom = np.sum((x - x_mean) ** 2)
        if abs(denom) < 1e-9:
            return 0.0
        slope = np.sum((x - x_mean) * (y - y_mean)) / denom
        # Normalize by price to make it scale-invariant
        return float(slope / (prices[0] + 1e-9))

    def _calculate_angle(self, slope: float) -> float:
        """Calculates trend angle in degrees from normalized slope."""
        # Scale slope for human-readable angle (heuristic scaling)
        return float(np.degrees(np.arctan(slope * self.ANGLE_SCALE)))

    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Measures 'fat tails' in return distribution."""
        if len(returns) < 4:
            return 0.0
        return float(stats.kurtosis(returns, fisher=True))

    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Measures asymmetry in return distribution."""
        if len(returns) < 3:
            return 0.0
        return float(stats.skew(returns))

    def _calculate_vol_of_vol(self, returns: np.ndarray, window: int | None = None) -> float:
        """Calculates volatility of volatility."""
        n = len(returns)
        if n < 4:
            return 0.0
        if window is None:
            window = max(2, n // 2)

        # Rolling standard deviation
        rolling_vol = pd.Series(returns).rolling(window=window).std(ddof=0).dropna().values
        if len(rolling_vol) < 2:
            return 0.0
        return float(np.std(rolling_vol) / (np.mean(rolling_vol) + 1e-9))

    def _calculate_volatility_clustering(self, returns: np.ndarray) -> float:
        """
        Calculates volatility clustering via autocorrelation of absolute returns.
        """
        if len(returns) < 5:
            return 0.0
        abs_rets = np.abs(returns)

        x = abs_rets[1:]
        y = abs_rets[:-1]

        if np.std(x) < 1e-9 or np.std(y) < 1e-9:
            return 0.0

        correlation_matrix = np.corrcoef(x, y)
        if correlation_matrix.shape == (2, 2):
            corr = correlation_matrix[0, 1]
            return float(corr) if not np.isnan(corr) else 0.0
        return 0.0

    def detect(self, data: pd.DataFrame) -> RegimeInfo:
        """
        Detect current market regime from OHLCV data.

        Args:
            data: DataFrame with OHLCV columns ('open', 'high', 'low', 'close', 'tick_volume').

        Returns:
            RegimeInfo object containing detected label, confidence, and transition score.
        """
        if len(data) < self.long_window:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
                raw_features={},
            )

        # 1. Use vectorized _extract_features to ensure consistency
        # We take a sufficient tail to compute all features accurately
        features_df = self._extract_features(data.tail(self.long_window + 1))
        if features_df.empty:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
                raw_features={},
            )

        last_row = features_df.iloc[-1]
        atr_ratio = float(last_row["atr_ratio"])
        slope = float(last_row["slope"])
        angle = self._calculate_angle(slope)

        # Raw features for explainability
        raw_features = last_row.to_dict()
        raw_features["angle"] = angle

        transition_probabilities = {}
        if self._gmm is not None:
            # Clustering-based detection
            X = last_row[self.FEATURE_COLUMNS].values.reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0)

            probs = self._gmm.predict_proba(X)[0]
            cluster_idx = int(np.argmax(probs))
            label = self._cluster_to_regime.get(cluster_idx, MarketRegime.RANGING)
            confidence = float(probs[cluster_idx])

            # Map all cluster probabilities to regime labels
            for idx, prob in enumerate(probs):
                regime_label = self._cluster_to_regime.get(idx, MarketRegime.RANGING).value
                transition_probabilities[regime_label] = transition_probabilities.get(
                    regime_label, 0.0
                ) + float(prob)

            # Transition score based on entropy of cluster probabilities
            # Max entropy for 6 clusters is ln(6) approx 1.79
            entropy = -np.sum(probs * np.log(probs + 1e-9))
            transition_score = float(entropy / 1.79)

            # Adjust transition score with historical transition probability if available
            if self.transition_matrix is not None and self._last_regime != MarketRegime.UNKNOWN:
                from_regime = self._last_regime.value
                to_regime = label.value
                if (
                    from_regime in self.transition_matrix.index
                    and to_regime in self.transition_matrix.columns
                ):
                    prob = self.transition_matrix.loc[from_regime, to_regime]
                    transition_score = (transition_score + (1.0 - prob)) / 2.0
        else:
            # Heuristic-based detection
            label, confidence, transition_score = self._apply_regime_logic(
                atr_ratio=atr_ratio,
                er=float(last_row["efficiency_ratio"]),
                slope=slope,
                z_score=float(last_row["z_score"]),
                vc=float(last_row["vol_clustering"]),
                angle=angle,
                vov=float(last_row["vol_of_vol"]),
            )
            transition_probabilities = {
                label.value: confidence,
                MarketRegime.UNKNOWN.value: 1.0 - confidence,
            }

        regime_info = RegimeInfo(
            label=label,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            transition_score=float(np.clip(transition_score, 0.0, 1.0)),
            volatility_index=float(atr_ratio),
            transition_probabilities=transition_probabilities,
            raw_features=raw_features,
        )

        if label != self._last_regime:
            logger.info(
                "regime_transition",
                previous=str(self._last_regime),
                current=str(label),
                confidence=regime_info.confidence,
                transition_score=regime_info.transition_score,
            )
            self._last_regime = label

        return regime_info

    def _apply_regime_logic(
        self,
        atr_ratio: float,
        er: float,
        slope: float,
        z_score: float,
        vc: float,
        angle: float,
        vov: float,
    ) -> tuple[MarketRegime, float, float]:
        """Heuristic logic to classify market regime."""
        label = MarketRegime.RANGING
        confidence = 0.5

        # NEWS_SHOCK: Extreme volatility spike + high efficiency + high vol-of-vol
        if (
            atr_ratio > self.THRESH_NEWS_SHOCK_ATR
            and er > self.THRESH_NEWS_SHOCK_ER
            and vov > self.THRESH_NEWS_SHOCK_VOV
        ):
            label = MarketRegime.NEWS_SHOCK
            confidence = min(atr_ratio / 5.0, 1.0)
        # VOLATILE_BREAKOUT: High volatility + high efficiency
        elif atr_ratio > self.THRESH_BREAKOUT_ATR and er > self.THRESH_BREAKOUT_ER:
            label = MarketRegime.VOLATILE_BREAKOUT
            confidence = er
        # TRENDING: High efficiency + clear angle
        elif er > self.THRESH_TRENDING_ER and abs(angle) > self.THRESH_TRENDING_ANGLE:
            label = MarketRegime.TRENDING
            confidence = er
        # MEAN_REVERSION: Extreme deviation + low efficiency
        elif abs(z_score) > self.THRESH_MEAN_REV_Z and er < self.THRESH_MEAN_REV_ER:
            label = MarketRegime.MEAN_REVERSION
            confidence = min(abs(z_score) / 4.0, 1.0)
        # LOW_VOLATILITY_DRIFT: Low volatility + steady slope + low vol-of-vol
        elif (
            atr_ratio < self.THRESH_DRIFT_ATR
            and abs(angle) > self.THRESH_DRIFT_ANGLE
            and vov < self.THRESH_DRIFT_VOV
        ):
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 0.7
        # RANGING: Default state
        else:
            label = MarketRegime.RANGING
            confidence = 1.0 - er

        # Transition score heuristic
        transition_score = (
            abs(atr_ratio - 1.0) * 0.3 + abs(er - 0.5) * 0.3 + abs(vc) * 0.2 + min(vov / 3.0, 0.2)
        )
        return label, confidence, transition_score

    def run_analysis(self, df: pd.DataFrame) -> RegimeAnalysisReport:
        """
        Analyze a historical DataFrame and generate a RegimeAnalysisReport.
        """
        from datetime import UTC, datetime

        from src.research.reporting import RegimeSummary

        if "regime" not in df.columns:
            df = self.label_history(df)

        counts = df["regime"].value_counts(normalize=True) * 100

        # Calculate durations per regime
        analysis_df = df.copy()
        analysis_df["regime_group"] = (
            analysis_df["regime"] != analysis_df["regime"].shift()
        ).cumsum()
        durations = analysis_df.groupby("regime_group")["regime"].agg(["first", "count"])
        avg_durations = durations.groupby("first")["count"].mean()

        # Calculate transition matrix
        regime_series = analysis_df["regime"]
        transitions = pd.crosstab(regime_series, regime_series.shift(-1), normalize="index")

        regime_list = []
        for label, freq in counts.items():
            if label == MarketRegime.UNKNOWN.value:
                continue

            # Determine profitability if 'returns' column exists
            profitability = "N/A"
            if "returns" in df.columns:
                pnl = df[df["regime"] == label]["returns"].mean()
                profitability = "High" if pnl > 0.0001 else ("Low" if pnl < -0.0001 else "Neutral")

            avg_dur = avg_durations.get(label, 0)

            regime_list.append(
                RegimeSummary(
                    label=str(label),
                    frequency_pct=float(freq),
                    avg_duration_bars=int(avg_dur),
                    profitability=profitability,
                )
            )

        return RegimeAnalysisReport(
            timestamp=datetime.now(UTC).isoformat(),
            counts_pct=counts.to_dict(),
            avg_durations=avg_durations.to_dict(),
            transitions=transitions,
            summary_text=f"Detected {len(counts)} distinct market regimes.",
            regime_list=regime_list,
        )

    def generate_summary(self, df: pd.DataFrame) -> Any:
        """
        Legacy method for backward compatibility. Use run_analysis instead.
        """
        return self.run_analysis(df).to_report_section()

    def label_history(self, data: pd.DataFrame, use_vectorized: bool = True) -> pd.DataFrame:
        """
        Adds regime columns to historical DataFrame.
        """
        if not use_vectorized:
            # Fallback to slow iterative approach
            df = data.copy()
            regimes = [MarketRegime.UNKNOWN.value] * len(df)
            confidences = [0.0] * len(df)
            transition_scores = [0.0] * len(df)
            volatility_indices = [0.0] * len(df)

            for i in range(self.long_window - 1, len(df)):
                info = self.detect(df.iloc[: i + 1])
                regimes[i] = info.label.value
                confidences[i] = info.confidence
                transition_scores[i] = info.transition_score
                volatility_indices[i] = info.volatility_index

            df["regime"] = regimes
            df["regime_confidence"] = confidences
            df["regime_transition_score"] = transition_scores
            df["volatility_index"] = volatility_indices
            return df

        # Vectorized implementation
        features = self._extract_features(data)
        if features.empty:
            return data

        df = data.copy()

        if self._gmm is not None:
            # Use GMM for vectorized labeling
            X = features.values
            # Handle NaNs in features
            X = np.nan_to_num(X, nan=0.0)

            probs = self._gmm.predict_proba(X)
            cluster_indices = np.argmax(probs, axis=1)

            regimes = [
                self._cluster_to_regime.get(idx, MarketRegime.RANGING).value
                for idx in cluster_indices
            ]
            confidences = np.max(probs, axis=1)

            # Vectorized entropy
            entropy = -np.sum(probs * np.log(probs + 1e-9), axis=1)
            transition_scores = entropy / 1.79
        else:
            # Vectorized heuristic (fully aligned with _apply_regime_logic)
            atr_ratio = features["atr_ratio"].values
            er = features["efficiency_ratio"].values
            slope = features["slope"].values
            z_score = features["z_score"].values
            angle = np.degrees(np.arctan(slope * self.ANGLE_SCALE))
            vov = features["vol_of_vol"].values
            vc = features["vol_clustering"].values

            regimes = np.array([MarketRegime.RANGING.value] * len(df), dtype=object)
            confidences = 1.0 - er

            # Masks for different regimes (ordered by precedence)
            news_mask = (
                (atr_ratio > self.THRESH_NEWS_SHOCK_ATR)
                & (er > self.THRESH_NEWS_SHOCK_ER)
                & (vov > self.THRESH_NEWS_SHOCK_VOV)
            )
            breakout_mask = (atr_ratio > self.THRESH_BREAKOUT_ATR) & (er > self.THRESH_BREAKOUT_ER)
            trending_mask = (er > self.THRESH_TRENDING_ER) & (
                np.abs(angle) > self.THRESH_TRENDING_ANGLE
            )
            mean_rev_mask = (np.abs(z_score) > self.THRESH_MEAN_REV_Z) & (
                er < self.THRESH_MEAN_REV_ER
            )
            drift_mask = (
                (atr_ratio < self.THRESH_DRIFT_ATR)
                & (np.abs(angle) > self.THRESH_DRIFT_ANGLE)
                & (vov < self.THRESH_DRIFT_VOV)
            )

            # Apply masks in precedence
            regimes[drift_mask] = MarketRegime.LOW_VOLATILITY_DRIFT.value
            confidences[drift_mask] = 0.7

            regimes[mean_rev_mask] = MarketRegime.MEAN_REVERSION.value
            confidences[mean_rev_mask] = np.clip(np.abs(z_score[mean_rev_mask]) / 4.0, 0, 1.0)

            regimes[trending_mask] = MarketRegime.TRENDING.value
            confidences[trending_mask] = er[trending_mask]

            regimes[breakout_mask] = MarketRegime.VOLATILE_BREAKOUT.value
            confidences[breakout_mask] = er[breakout_mask]

            regimes[news_mask] = MarketRegime.NEWS_SHOCK.value
            confidences[news_mask] = np.clip(atr_ratio[news_mask] / 5.0, 0, 1.0)

            transition_scores = (
                np.abs(atr_ratio - 1.0) * 0.3
                + np.abs(er - 0.5) * 0.3
                + np.abs(vc) * 0.2
                + np.clip(vov / 3.0, 0, 0.2)
            )

        # Mask out burn-in period
        regimes[: self.long_window - 1] = [MarketRegime.UNKNOWN.value] * (self.long_window - 1)
        confidences[: self.long_window - 1] = 0.0
        transition_scores[: self.long_window - 1] = 0.0

        df["regime"] = regimes
        df["regime_confidence"] = confidences
        df["regime_transition_score"] = transition_scores
        df["volatility_index"] = features["atr_ratio"]

        return df

    def _extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts statistical features for clustering or detection.
        Fully vectorized implementation for institutional performance.
        """
        if len(data) < self.long_window:
            return pd.DataFrame()

        # Vectorized feature extraction for historical data or single step
        close = data["close"]
        high = data["high"]
        low = data["low"]

        # 1. Volatility (ATR Ratio)
        tr = np.maximum(
            high - low,
            np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))),
        ).fillna(high - low)
        atr_short = tr.rolling(window=self.window).mean()
        atr_long = tr.rolling(window=self.long_window).mean()
        atr_ratio = atr_short / (atr_long + 1e-9)
        atr_ratio = atr_ratio.where(atr_long >= 1e-9, 1.0).fillna(1.0)

        # 2. Efficiency Ratio
        net_change = (close - close.shift(self.window - 1)).abs()
        abs_changes = (close - close.shift(1)).abs().rolling(window=self.window - 1).sum()
        er = net_change / (abs_changes + 1e-9)
        er = er.where(abs_changes >= 1e-9, 0.5).fillna(0.5)

        # 3. Returns and derived stats
        returns = close.pct_change(fill_method=None).fillna(0)
        # Fast vectorized higher-order moments
        kurt = returns.rolling(window=self.window).kurt().fillna(0.0)
        skew = returns.rolling(window=self.window).skew().fillna(0.0)

        # 4. Slope and Z-Score
        # Vectorized linear regression slope: (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - (sum(x))^2)
        n = self.window
        indices = np.arange(len(close))
        s_x = n * (n - 1) / 2.0
        s_x2 = n * (n - 1) * (2 * n - 1) / 6.0
        s_y = close.rolling(window=n).sum()
        s_iy = (close * indices).rolling(window=n).sum()
        start_indices = indices - n + 1
        sum_relative_iy = s_iy - start_indices * s_y
        slope_num = n * sum_relative_iy - s_x * s_y
        slope_den = n * s_x2 - s_x**2
        slope = ((slope_num / (slope_den + 1e-9)) / (close.shift(n - 1) + 1e-9)).fillna(0.0)

        ma = close.rolling(window=self.window).mean()
        std = close.rolling(window=self.window).std(ddof=0)
        z_score = ((close - ma) / (std + 1e-9)).fillna(0.0)

        # 5. Vol-of-vol and Vol Clustering
        # Vol-of-vol: std(rolling_vol) / mean(rolling_vol)
        vov_window = max(2, self.window // 2)
        rolling_vol = returns.rolling(window=vov_window).std(ddof=0)

        adj_window = self.window - vov_window + 1
        if adj_window >= 2:
            vov_std = rolling_vol.rolling(window=adj_window).std(ddof=0)
            vov_mean = rolling_vol.rolling(window=adj_window).mean()
            vov = (vov_std / (vov_mean + 1e-9)).fillna(0.0)
        else:
            vov = pd.Series(0.0, index=close.index)

        # Volatility Clustering: Correlation of absolute returns with lagged absolute returns
        abs_rets = returns.abs()
        vc = abs_rets.rolling(window=self.window).corr(abs_rets.shift(1)).fillna(0.0)

        features = pd.DataFrame(
            {
                "atr_ratio": atr_ratio,
                "efficiency_ratio": er,
                "slope": slope,
                "z_score": z_score,
                "kurtosis": kurt,
                "skewness": skew,
                "vol_of_vol": vov,
                "vol_clustering": vc,
            }
        )

        return features[self.FEATURE_COLUMNS]

    def fit(self, data: pd.DataFrame, n_clusters: int = 6) -> None:
        """
        Trains GMM on historical data to learn market regimes.
        Automatically maps clusters to labels and calculates a transition matrix.

        Args:
            data: Historical OHLCV DataFrame for training.
            n_clusters: Number of clusters for Gaussian Mixture Model (default 6).
        """
        features = self._extract_features(data)
        if features.empty or len(features) < self.long_window * 2:
            logger.warning("Insufficient data for fitting GMM")
            return

        # Skip the burn-in period and handle NaNs
        X = features.iloc[self.long_window :].values
        X = np.nan_to_num(X, nan=0.0)

        self._gmm = GaussianMixture(
            n_components=n_clusters, covariance_type="full", random_state=42, n_init=5
        )
        self._gmm.fit(X)

        # Automated cluster-to-regime mapping based on centroids
        self._map_clusters(self._gmm.means_)

        # Calculate transition matrix from training data
        self._calculate_transition_matrix(features.iloc[self.long_window :])

        logger.info("gmm_fit_complete", n_clusters=n_clusters)

    def save_model(self, filepath: str) -> None:
        """
        Persists the GMM model and cluster mappings to disk.
        """
        if self._gmm is None:
            logger.warning("No GMM model to save.")
            return

        state = {
            "gmm": self._gmm,
            "cluster_to_regime": self._cluster_to_regime,
            "transition_matrix": self.transition_matrix,
            "window": self.window,
            "long_window": self.long_window,
        }
        joblib.dump(state, filepath)
        logger.info("model_saved", path=filepath)

    def load_model(self, filepath: str) -> None:
        """
        Loads a persisted GMM model and state from disk.
        Institutional security: Validates path and permissions before deserialization.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            logger.error("Model file not found: %s", filepath)
            return

        # Security: Path validation - restrict to project's models directory or /tmp
        try:
            from src.core.config import ROOT

            models_dir = (ROOT / "models").resolve()

            # Robust path validation using is_relative_to (Python 3.9+)
            # This prevents bypasses like /app/models_attacker/
            is_in_models = False
            with contextlib.suppress(ValueError):
                is_in_models = path.is_relative_to(models_dir)

            is_in_tmp = False
            with contextlib.suppress(ValueError):
                is_in_tmp = path.is_relative_to("/tmp") or path.is_relative_to("/var/tmp")

            if not (is_in_models or is_in_tmp):
                logger.error(
                    "Security violation: Attempted to load model from untrusted path: %s", path
                )
                return
        except ImportError as e:
            # Fail-closed if security constraints cannot be verified
            logger.error("Security violation: Could not verify model path safety: %s", e)
            return

        # Security: Permission check - ensure no world-writable/readable access (Linux/Mac)
        # Aligned with ConfigValidator: check both group and others (0o077 mask)
        if os.name != "nt":
            mode = os.stat(path).st_mode
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                logger.error("Security violation: Insecure permissions for model file: %s", path)
                return

        try:
            state = joblib.load(path)
            self._gmm = state.get("gmm")
            self._cluster_to_regime = state.get("cluster_to_regime", {})
            self.transition_matrix = state.get("transition_matrix")
            self.window = state.get("window", self.window)
            self.long_window = state.get("long_window", self.long_window)
            logger.info("model_loaded", path=str(path))
        except Exception as e:
            logger.error("Failed to load model from %s: %s", filepath, e)

    def _calculate_transition_matrix(self, features: pd.DataFrame) -> None:
        """Calculates transition probability matrix from fitted GMM on training data."""
        if self._gmm is None:
            return

        X = features.values
        X = np.nan_to_num(X, nan=0.0)
        probs = self._gmm.predict_proba(X)
        cluster_indices = np.argmax(probs, axis=1)
        regimes = [
            self._cluster_to_regime.get(idx, MarketRegime.RANGING).value for idx in cluster_indices
        ]

        regime_series = pd.Series(regimes)
        self.transition_matrix = pd.crosstab(
            regime_series, regime_series.shift(-1), normalize="index"
        )

    def _map_clusters(self, centroids: np.ndarray) -> None:
        """Maps GMM clusters to MarketRegime enum using centroid heuristics."""
        self._cluster_to_regime = {}
        feat_map = {name: i for i, name in enumerate(self.FEATURE_COLUMNS)}

        for i, center in enumerate(centroids):
            atr_ratio = center[feat_map["atr_ratio"]]
            er = center[feat_map["efficiency_ratio"]]
            slope = center[feat_map["slope"]]
            z_score = center[feat_map["z_score"]]
            vov = center[feat_map["vol_of_vol"]]

            angle = self._calculate_angle(slope)

            # Thresholds synchronized with _apply_regime_logic
            if (
                atr_ratio > self.THRESH_NEWS_SHOCK_ATR
                and er > self.THRESH_NEWS_SHOCK_ER
                and vov > self.THRESH_NEWS_SHOCK_VOV
            ):
                self._cluster_to_regime[i] = MarketRegime.NEWS_SHOCK
            elif atr_ratio > self.THRESH_BREAKOUT_ATR and er > self.THRESH_BREAKOUT_ER:
                self._cluster_to_regime[i] = MarketRegime.VOLATILE_BREAKOUT
            elif er > self.THRESH_TRENDING_ER and abs(angle) > self.THRESH_TRENDING_ANGLE:
                self._cluster_to_regime[i] = MarketRegime.TRENDING
            elif abs(z_score) > self.THRESH_MEAN_REV_Z and er < self.THRESH_MEAN_REV_ER:
                self._cluster_to_regime[i] = MarketRegime.MEAN_REVERSION
            elif (
                atr_ratio < self.THRESH_DRIFT_ATR
                and abs(angle) > self.THRESH_DRIFT_ANGLE
                and vov < self.THRESH_DRIFT_VOV
            ):
                self._cluster_to_regime[i] = MarketRegime.LOW_VOLATILITY_DRIFT
            else:
                self._cluster_to_regime[i] = MarketRegime.RANGING

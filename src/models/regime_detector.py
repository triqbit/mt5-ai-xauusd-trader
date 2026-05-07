"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection for XAUUSD.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """XAUUSD Market Regimes."""

    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class RegimeInfo(BaseModel):
    """Structured regime detection output."""

    label: MarketRegime = Field(..., description="Detected regime label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    transition_score: float = Field(..., description="Likelihood of a regime transition")
    volatility_index: float = Field(..., description="Normalized volatility metric")


class RegimeDetector:
    """
    Detects market regimes using statistical price features.
    Optimized for XAUUSD M5/M15 timeframes.
    """

    def __init__(self, window: int = 20, long_window: int = 100) -> None:
        self.window = window
        self.long_window = long_window
        self._last_regime: MarketRegime = MarketRegime.UNKNOWN
        self._gmm: GaussianMixture | None = None
        self._cluster_to_regime: dict[int, MarketRegime] = {}

    def _calculate_efficiency_ratio(self, prices: np.ndarray) -> float:
        """Kaufman Efficiency Ratio: net change / sum of absolute changes."""
        if len(prices) < 2:
            return 0.0
        net_change = abs(prices[-1] - prices[0])
        abs_changes = np.abs(np.diff(prices))
        sum_abs_changes = np.sum(abs_changes)
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
        return float(np.degrees(np.arctan(slope * 1000)))

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

    def _calculate_vol_of_vol(self, returns: np.ndarray, window: int = 10) -> float:
        """Calculates volatility of volatility."""
        if len(returns) < window + 2:
            return 0.0
        # Rolling standard deviation
        rolling_vol = pd.Series(returns).rolling(window=window).std().dropna().values
        if len(rolling_vol) < 2:
            return 0.0
        return float(np.std(rolling_vol) / (np.mean(rolling_vol) + 1e-9))

    def _calculate_volatility_clustering(self, returns: np.ndarray) -> float:
        """
        Calculates volatility clustering via autocorrelation of absolute returns.
        """
        if len(returns) < 10:
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
        """
        if len(data) < self.long_window:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
            )

        lookback = self.long_window + 1
        subset = data.iloc[-lookback:]
        close = subset["close"].values
        high = subset["high"].values
        low = subset["low"].values

        # 1. Volatility (ATR Ratio)
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
        )
        if len(subset) <= self.long_window:
            tr = np.insert(tr, 0, high[0] - low[0])

        atr_short = np.mean(tr[-self.window :])
        atr_long = np.mean(tr[-self.long_window :])
        atr_ratio = atr_short / (atr_long + 1e-9)

        # 2. Efficiency Ratio
        er = self._calculate_efficiency_ratio(close[-self.window :])

        # 3. Price Slope
        slope = self._calculate_slope(close[-self.window :])

        # 4. Z-Score
        ma = np.mean(close[-self.window :])
        std = np.std(close[-self.window :]) + 1e-9
        z_score = (close[-1] - ma) / std

        # 5. Volatility Clustering
        returns = np.diff(close) / (close[:-1] + 1e-9)
        vc = self._calculate_volatility_clustering(returns[-self.window :])

        # 6. Higher-order stats
        kurt = self._calculate_kurtosis(returns[-self.window :])
        skew = self._calculate_skewness(returns[-self.window :])
        vov = self._calculate_vol_of_vol(returns[-self.window :])
        angle = self._calculate_angle(slope)

        if self._gmm is not None:
            # Clustering-based detection
            X = np.array([[atr_ratio, er, slope, z_score, kurt, skew]])
            probs = self._gmm.predict_proba(X)[0]
            cluster_idx = int(np.argmax(probs))
            label = self._cluster_to_regime.get(cluster_idx, MarketRegime.RANGING)
            confidence = float(probs[cluster_idx])

            # Transition score based on entropy of cluster probabilities
            # Max entropy for 6 clusters is ln(6) approx 1.79
            entropy = -np.sum(probs * np.log(probs + 1e-9))
            transition_score = float(entropy / 1.79)
        else:
            # Heuristic-based detection
            label, confidence, transition_score = self._apply_regime_logic(
                atr_ratio, er, slope, z_score, vc, vov, angle
            )

        regime_info = RegimeInfo(
            label=label,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            transition_score=float(np.clip(transition_score, 0.0, 1.0)),
            volatility_index=float(atr_ratio),
        )

        if label != self._last_regime:
            logger.debug("Regime transition: %s -> %s", self._last_regime, label)
            self._last_regime = label

        return regime_info

    def _apply_regime_logic(
        self,
        atr_ratio: float,
        er: float,
        slope: float,
        z_score: float,
        vc: float,
        vov: float = 0.0,
        angle: float = 0.0,
    ) -> tuple[MarketRegime, float, float]:
        """Heuristic logic to classify market regime."""
        label = MarketRegime.RANGING
        confidence = 0.5

        if atr_ratio > 2.5 and er > 0.7:
            label = MarketRegime.NEWS_SHOCK
            confidence = min(atr_ratio / 5.0, 1.0)
        elif (atr_ratio > 1.25 and er > 0.5) or vov > 1.5:
            label = MarketRegime.VOLATILE_BREAKOUT
            confidence = er
        elif (er > 0.4 and abs(slope) > 0.00006) or abs(angle) > 25.0:
            label = MarketRegime.TRENDING
            confidence = er
        elif abs(z_score) > 1.8 and er < 0.4:
            label = MarketRegime.MEAN_REVERSION
            confidence = min(abs(z_score) / 4.0, 1.0)
        elif atr_ratio < 0.9 and abs(slope) > 0.00003:
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 0.7
        else:
            label = MarketRegime.RANGING
            confidence = 1.0 - er

        transition_score = abs(atr_ratio - 1.0) * 0.4 + abs(er - 0.5) * 0.4 + abs(vc) * 0.2
        return label, confidence, transition_score

    def generate_summary(self, df: pd.DataFrame) -> Any:
        """
        Analyze a historical DataFrame and generate a RegimeSection for ResearchReporter.
        """
        from src.research.reporting import RegimeSection, RegimeSummary

        if "regime" not in df.columns:
            df = self.label_history(df)

        counts = df["regime"].value_counts(normalize=True) * 100

        # Calculate durations per regime
        analysis_df = df.copy()
        analysis_df["regime_group"] = (analysis_df["regime"] != analysis_df["regime"].shift()).cumsum()
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

        # Transition insights
        top_transitions = []
        for reg in transitions.index:
            if reg == MarketRegime.UNKNOWN.value:
                continue
            # Get most likely transition that is NOT to itself
            other_regs = transitions.columns[transitions.columns != reg]
            if not other_regs.empty:
                valid_targets = [t for t in other_regs if t != MarketRegime.UNKNOWN.value]
                if valid_targets:
                    target = transitions.loc[reg, valid_targets].idxmax()
                    prob = transitions.loc[reg, target]
                    if prob > 0.05:
                        top_transitions.append(f"{reg} -> {target} ({prob:.1%})")

        transition_txt = " | ".join(top_transitions[:3])
        if not transition_txt:
            transition_txt = "No significant transitions detected."

        return RegimeSection(
            summary=f"Detected {len(counts)} distinct market regimes.",
            regimes=regime_list,
            transition_insights=f"Stability: {avg_durations.mean():.1f} bars. Common paths: {transition_txt}",
        )

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
            # Vectorized heuristic (simplified for performance)
            atr_ratio = features["atr_ratio"].values
            er = features["efficiency_ratio"].values
            slope = features["slope"].values
            z_score = features["z_score"].values

            regimes = [MarketRegime.RANGING.value] * len(df)
            confidences = 1.0 - er

            # Masks for different regimes
            news_mask = (atr_ratio > 2.5) & (er > 0.7)
            breakout_mask = (atr_ratio > 1.25) & (er > 0.5)
            trending_mask = (er > 0.4) & (np.abs(slope) > 0.00006)
            mean_rev_mask = (np.abs(z_score) > 1.8) & (er < 0.4)
            drift_mask = (atr_ratio < 0.9) & (np.abs(slope) > 0.00003)

            # Apply in order of precedence
            for i in range(len(regimes)):
                if news_mask[i]:
                    regimes[i] = MarketRegime.NEWS_SHOCK.value
                    confidences[i] = min(atr_ratio[i] / 5.0, 1.0)
                elif breakout_mask[i]:
                    regimes[i] = MarketRegime.VOLATILE_BREAKOUT.value
                    confidences[i] = er[i]
                elif trending_mask[i]:
                    regimes[i] = MarketRegime.TRENDING.value
                    confidences[i] = er[i]
                elif mean_rev_mask[i]:
                    regimes[i] = MarketRegime.MEAN_REVERSION.value
                    confidences[i] = min(abs(z_score[i]) / 4.0, 1.0)
                elif drift_mask[i]:
                    regimes[i] = MarketRegime.LOW_VOLATILITY_DRIFT.value
                    confidences[i] = 0.7

            transition_scores = np.abs(atr_ratio - 1.0) * 0.4 + np.abs(er - 0.5) * 0.4

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
        """Extracts statistical features for clustering or detection."""
        if len(data) < self.long_window:
            return pd.DataFrame()

        # Vectorized feature extraction for historical data or single step
        close = data["close"]
        high = data["high"]
        low = data["low"]

        # 1. Volatility
        tr = np.maximum(
            high - low,
            np.maximum(np.abs(high - close.shift(1)), np.abs(low - close.shift(1))),
        ).fillna(high - low)
        atr_short = tr.rolling(window=self.window).mean()
        atr_long = tr.rolling(window=self.long_window).mean()
        atr_ratio = atr_short / (atr_long + 1e-9)

        # 2. Efficiency Ratio (matches iterative: window bars -> window-1 intervals)
        net_change = (close - close.shift(self.window - 1)).abs()
        abs_changes = (close - close.shift(1)).abs().rolling(window=self.window - 1).sum()
        er = net_change / (abs_changes + 1e-9)

        # 3. Returns and derived stats
        returns = close.pct_change().fillna(0)
        kurt = returns.rolling(window=self.window).apply(
            lambda x: stats.kurtosis(x, fisher=True), raw=True
        )
        skew = returns.rolling(window=self.window).apply(lambda x: stats.skew(x), raw=True)

        # 4. Slope and Z-Score
        ma = close.rolling(window=self.window).mean()
        std = close.rolling(window=self.window).std()
        z_score = (close - ma) / (std + 1e-9)

        # For slope, we'll use a simpler version for vectorization or just apply our method
        def get_slope(x):
            return self._calculate_slope(x)

        slope = close.rolling(window=self.window).apply(get_slope, raw=True)

        features = pd.DataFrame(
            {
                "atr_ratio": atr_ratio,
                "efficiency_ratio": er,
                "slope": slope,
                "z_score": z_score,
                "kurtosis": kurt,
                "skewness": skew,
            }
        ).fillna(0)

        return features

    def fit(self, data: pd.DataFrame, n_clusters: int = 6) -> None:
        """
        Trains GMM on historical data to learn market regimes.
        """
        features = self._extract_features(data)
        if features.empty or len(features) < self.long_window * 2:
            logger.warning("Insufficient data for fitting GMM")
            return

        # Skip the burn-in period
        X = features.iloc[self.long_window :].values

        self._gmm = GaussianMixture(
            n_components=n_clusters, covariance_type="full", random_state=42, n_init=5
        )
        self._gmm.fit(X)

        # Automated cluster-to-regime mapping based on centroids
        self._map_clusters(self._gmm.means_)
        logger.info("RegimeDetector GMM fitted with %d clusters", n_clusters)

    def _map_clusters(self, centroids: np.ndarray) -> None:
        """Maps GMM clusters to MarketRegime enum using centroid heuristics."""
        # Feature order: atr_ratio, efficiency_ratio, slope, z_score, kurtosis, skewness
        self._cluster_to_regime = {}
        for i, center in enumerate(centroids):
            atr_ratio, er, slope, z_score, kurt, skew = center

            if atr_ratio > 1.8 and er > 0.6:
                self._cluster_to_regime[i] = MarketRegime.NEWS_SHOCK
            elif atr_ratio > 1.2 and er > 0.4:
                self._cluster_to_regime[i] = MarketRegime.VOLATILE_BREAKOUT
            elif er > 0.4 and abs(slope) > 0.00005:
                self._cluster_to_regime[i] = MarketRegime.TRENDING
            elif abs(z_score) > 1.5 and er < 0.3:
                self._cluster_to_regime[i] = MarketRegime.MEAN_REVERSION
            elif atr_ratio < 0.9 and abs(slope) > 0.00002:
                self._cluster_to_regime[i] = MarketRegime.LOW_VOLATILITY_DRIFT
            else:
                self._cluster_to_regime[i] = MarketRegime.RANGING

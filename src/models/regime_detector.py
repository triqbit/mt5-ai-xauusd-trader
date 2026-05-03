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
from typing import Any, Dict, Optional, Tuple, List

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

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
    Supports both heuristic and adaptive clustering (GMM) modes.
    """

    def __init__(
        self,
        window: int = 20,
        long_window: int = 100,
        use_clustering: bool = False,
    ) -> None:
        self.window = window
        self.long_window = long_window
        self.use_clustering = use_clustering
        self._last_regime: MarketRegime = MarketRegime.UNKNOWN
        self._gmm: Any = None
        self._cluster_map: Dict[int, MarketRegime] = {}

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
        denom = n * np.sum(x**2) - (np.sum(x)) ** 2
        if abs(denom) < 1e-9:
            return 0.0
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denom
        return float(slope / (prices[0] + 1e-9))

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

    def _calculate_features_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized feature calculation for an entire DataFrame."""
        feats = pd.DataFrame(index=df.index)
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # 1. ATR Ratio
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        # Ensure first TR is high-low to match detect() behavior
        tr.iloc[0] = high.iloc[0] - low.iloc[0]

        atr_short = tr.rolling(window=self.window).mean()
        atr_long = tr.rolling(window=self.long_window).mean()
        feats["atr_ratio"] = atr_short / (atr_long + 1e-9)

        # 2. Efficiency Ratio
        # Use window+1 prices to get 'window' intervals
        net_change = (close - close.shift(self.window)).abs()
        sum_abs_changes = (close - close.shift(1)).abs().rolling(window=self.window).sum()
        feats["er"] = net_change / (sum_abs_changes + 1e-9)

        # 3. Slope (rolling linear regression)
        def get_slope(y):
            n = len(y)
            x = np.arange(n)
            denom = n * np.sum(x**2) - (np.sum(x)) ** 2
            if abs(denom) < 1e-9: return 0.0
            slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denom
            return slope / (y[0] + 1e-9)

        feats["slope"] = close.rolling(window=self.window).apply(get_slope, raw=True)

        # 4. Z-Score
        ma = close.rolling(window=self.window).mean()
        std = close.rolling(window=self.window).std() + 1e-9
        feats["z_score"] = (close - ma) / std

        # 5. Volatility Clustering
        returns = close.pct_change()
        def get_vc(r):
            if len(r) < 10: return 0.0
            abs_rets = np.abs(r)
            x, y = abs_rets[1:], abs_rets[:-1]
            if np.std(x) < 1e-9 or np.std(y) < 1e-9: return 0.0
            return np.corrcoef(x, y)[0, 1]

        feats["vc"] = returns.rolling(window=self.window).apply(get_vc, raw=True)

        return feats

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

        if self.use_clustering and self._gmm is not None:
            return self._detect_clustering(data)

        # Heuristic detection
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
        # Match vectorized logic by always inserting first bar's high-low
        tr = np.insert(tr, 0, high[0] - low[0])

        atr_short = np.mean(tr[-self.window :])
        atr_long = np.mean(tr[-self.long_window :])
        atr_ratio = atr_short / (atr_long + 1e-9)

        # 2. Efficiency Ratio (requires window+1 prices for 'window' intervals)
        er = self._calculate_efficiency_ratio(close[-(self.window + 1) :])

        # 3. Price Slope
        slope = self._calculate_slope(close[-self.window :])

        # 4. Z-Score
        ma = np.mean(close[-self.window :])
        std = np.std(close[-self.window :]) + 1e-9
        z_score = (close[-1] - ma) / std

        # 5. Volatility Clustering
        returns = np.diff(close) / (close[:-1] + 1e-9)
        vc = self._calculate_volatility_clustering(returns[-self.window :])

        label, confidence, transition_score = self._apply_regime_logic(
            atr_ratio, er, slope, z_score, vc
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
        self, atr_ratio: float, er: float, slope: float, z_score: float, vc: float
    ) -> Tuple[MarketRegime, float, float]:
        """
        Heuristic logic to classify market regime based on statistical thresholds.
        Optimized for Gold (XAUUSD) volatility profiles.
        """
        if atr_ratio > 3.0:
            label = MarketRegime.NEWS_SHOCK
            confidence = min(atr_ratio / 6.0, 1.0)
        elif atr_ratio > 1.4 and er > 0.6:
            label = MarketRegime.VOLATILE_BREAKOUT
            confidence = (er + min(atr_ratio / 3.0, 1.0)) / 2.0
        elif er > 0.5 and abs(slope) > 0.00008:
            label = MarketRegime.TRENDING
            confidence = er
        elif abs(z_score) > 2.0 and er < 0.3:
            label = MarketRegime.MEAN_REVERSION
            confidence = min(abs(z_score) / 4.0, 1.0)
        elif atr_ratio < 0.8 and abs(slope) > 0.00004:
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 1.0 - atr_ratio
        else:
            label = MarketRegime.RANGING
            confidence = 1.0 - er

        # Transition score: measures how far features are from 'stable' regime centers
        # Higher score indicates higher likelihood of imminent regime shift
        transition_score = (
            abs(atr_ratio - 1.0) * 0.4 +
            abs(er - 0.4) * 0.3 +
            abs(vc) * 0.3
        )

        return label, float(np.clip(confidence, 0.0, 1.0)), float(np.clip(transition_score, 0.0, 1.0))

    def label_history(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Adds regime columns to historical DataFrame using vectorized feature calculation.
        """
        df = data.copy()

        # Calculate features in a vectorized way
        feats = self._calculate_features_df(df)

        # Determine labels
        if self.use_clustering and self._gmm is not None:
            # Clustering path (vectorized GMM)
            X = feats.dropna()
            clusters = self._gmm.predict(X)

            regimes = [MarketRegime.UNKNOWN.value] * len(df)
            confidences = [0.0] * len(df)

            probs = self._gmm.predict_proba(X)
            transition_scores = [0.0] * len(df)

            for i, (idx, row) in enumerate(X.iterrows()):
                pos = df.index.get_loc(idx)
                cluster = clusters[i]
                regimes[pos] = self._cluster_map.get(cluster, MarketRegime.UNKNOWN).value
                conf = np.max(probs[i])
                confidences[pos] = conf
                transition_scores[pos] = 1.0 - conf

            df["regime"] = regimes
            df["regime_confidence"] = confidences
            df["regime_transition_score"] = transition_scores
            df["volatility_index"] = feats["atr_ratio"]
        else:
            # Heuristic path (partially vectorized)
            # Use np.vectorize or just loop over the calculated features (faster than recalculating features in a loop)
            regimes = [MarketRegime.UNKNOWN.value] * len(df)
            confidences = [0.0] * len(df)
            transition_scores = [0.0] * len(df)

            # Drop NaN rows where features couldn't be calculated
            valid_feats = feats.dropna()

            for idx, row in valid_feats.iterrows():
                label, conf, trans = self._apply_regime_logic(
                    row["atr_ratio"], row["er"], row["slope"], row["z_score"], row["vc"]
                )
                pos = df.index.get_loc(idx)
                regimes[pos] = label.value
                confidences[pos] = conf
                transition_scores[pos] = trans

            df["regime"] = regimes
            df["regime_confidence"] = confidences
            df["regime_transition_score"] = transition_scores
            df["volatility_index"] = feats["atr_ratio"]

        return df

    def generate_summary(self, df: pd.DataFrame) -> Any:
        """
        Analyze a historical DataFrame and generate a RegimeSection for ResearchReporter.
        """
        from src.research.reporting import RegimeSection, RegimeSummary

        if "regime" not in df.columns:
            df = self.label_history(df)

        counts = df["regime"].value_counts(normalize=True) * 100

        # Calculate avg duration (rough estimate from changes)
        df["regime_change"] = df["regime"] != df["regime"].shift(1)
        regime_switches = df["regime_change"].sum()
        avg_duration = len(df) / regime_switches if regime_switches > 0 else len(df)

        regime_list = []
        for label, freq in counts.items():
            if label == MarketRegime.UNKNOWN.value: continue

            # Determine profitability if 'returns' column exists
            profitability = "N/A"
            if "returns" in df.columns:
                pnl = df[df["regime"] == label]["returns"].mean()
                profitability = "High" if pnl > 0.0001 else ("Low" if pnl < -0.0001 else "Neutral")

            regime_list.append(
                RegimeSummary(
                    label=str(label),
                    frequency_pct=float(freq),
                    avg_duration_bars=int(avg_duration),  # Simplified
                    profitability=profitability,
                )
            )

        return RegimeSection(
            summary=f"Detected {len(counts)} distinct market regimes.",
            regimes=regime_list,
            transition_insights=f"Average regime stability: {avg_duration:.1f} bars.",
        )

    def fit(self, data: pd.DataFrame) -> None:
        """Trains GMM for adaptive regime detection."""
        from sklearn.mixture import GaussianMixture

        feats = self._calculate_features_df(data).dropna()
        if len(feats) < self.long_window:
            logger.warning("Insufficient data for GMM fit.")
            return

        self._gmm = GaussianMixture(n_components=len(MarketRegime) - 1, random_state=42)
        self._gmm.fit(feats)

        # Map clusters to MarketRegime based on heuristic average of cluster centers
        centers = self._gmm.means_
        for i, center in enumerate(centers):
            # center indices: 0: atr_ratio, 1: er, 2: slope, 3: z_score, 4: vc
            atr_ratio, er, slope, z_score, vc = center
            label, _, _ = self._apply_regime_logic(atr_ratio, er, slope, z_score, vc)
            self._cluster_map[i] = label

        logger.info("GMM Regime Detector fitted with %d clusters.", len(self._cluster_map))

    def _detect_clustering(self, data: pd.DataFrame) -> RegimeInfo:
        """Internal detection using GMM."""
        feats = self._calculate_features_df(data).iloc[-1:]
        if feats.isnull().values.any():
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
            )

        cluster = self._gmm.predict(feats)[0]
        probs = self._gmm.predict_proba(feats)[0]

        label = self._cluster_map.get(cluster, MarketRegime.UNKNOWN)
        confidence = np.max(probs)

        # Transition score can be 1 - prob of current cluster
        transition_score = 1.0 - confidence

        return RegimeInfo(
            label=label,
            confidence=float(confidence),
            transition_score=float(transition_score),
            volatility_index=float(feats["atr_ratio"].iloc[0]),
        )

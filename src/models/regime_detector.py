"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection system using statistical OHLCV features.
Classifies market state into: trending, ranging, volatile breakout,
low-volatility drift, news shock, and mean-reversion.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RegimeLabel(str, Enum):
    """Enumeration of supported market regimes."""

    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"


class MarketRegime(BaseModel):
    """
    Typed market regime object containing classification results.

    Attributes:
        label: The classified regime label.
        confidence: Probability or confidence score (0.0 to 1.0).
        transition_score: Score indicating likelihood of regime shift (0.0 to 1.0).
        features: Optional dictionary of features used for detection.
    """

    label: RegimeLabel
    confidence: float = Field(ge=0.0, le=1.0)
    transition_score: float = Field(ge=0.0, le=1.0)
    features: Optional[Dict[str, float]] = None


class RegimeDetector:
    """
    Statistical market regime detector for XAUUSD and other instruments.
    Uses multi-window ATR, slope, and volatility clustering to classify market state.
    """

    def __init__(
        self,
        lookback_period: int = 20,
        volatility_window: int = 50,
        threshold_trending: float = 0.5,
        threshold_volatile: float = 1.5,
    ) -> None:
        """
        Initialize the detector with configurable thresholds.

        Args:
            lookback_period: Period for slope and ATR calculations.
            volatility_window: Period for long-term volatility baseline.
            threshold_trending: Z-score threshold for slope to be considered trending.
            threshold_volatile: Z-score threshold for ATR to be considered volatile.
        """
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.threshold_trending = threshold_trending
        self.threshold_volatile = threshold_volatile

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime from OHLCV data.

        Args:
            df: DataFrame containing 'open', 'high', 'low', 'close', 'volume' columns.

        Returns:
            MarketRegime object with classification and confidence.
        """
        if len(df) < self.volatility_window:
            logger.warning("Insufficient data for regime detection. Returning RANGING by default.")
            return MarketRegime(label=RegimeLabel.RANGING, confidence=0.5, transition_score=0.0)

        features = self._extract_features(df)
        label, confidence = self._classify(features)

        # Transition score calculation based on rate of change in volatility and slope
        transition_score = self._calculate_transition_score(df)

        return MarketRegime(
            label=label,
            confidence=confidence,
            transition_score=transition_score,
            features=features,
        )

    def _extract_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract statistical features from OHLCV data."""
        # Calculate ATR
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=self.lookback_period).mean()

        # Long-term ATR for normalization
        atr_baseline = tr.rolling(window=self.volatility_window).mean()

        current_atr = atr.iloc[-1]
        baseline_atr = atr_baseline.iloc[-1]
        atr_ratio = current_atr / (baseline_atr + 1e-9)

        # Calculate Slope (Normalized)
        close = df["close"]
        x = np.arange(self.lookback_period)
        y = close.iloc[-self.lookback_period :].values
        slope, _ = np.polyfit(x, y, 1)
        # Normalize slope by price level to get percentage change
        norm_slope = (slope / close.iloc[-1]) * 100

        # Calculate ADX-like Trend Strength (simplified)
        # Ratio of net displacement to path length
        net_move = abs(close.iloc[-1] - close.iloc[-self.lookback_period])
        total_move = tr.iloc[-self.lookback_period :].sum()
        efficiency_ratio = net_move / (total_move + 1e-9)

        # Volatility Clustering (Standard Deviation of returns)
        returns = close.pct_change()
        volatility = returns.rolling(window=self.lookback_period).std().iloc[-1]
        vol_baseline = returns.rolling(window=self.volatility_window).std().iloc[-1]
        vol_ratio = volatility / (vol_baseline + 1e-9)

        return {
            "atr_ratio": float(atr_ratio),
            "norm_slope": float(norm_slope),
            "efficiency_ratio": float(efficiency_ratio),
            "vol_ratio": float(vol_ratio),
        }

    def _classify(self, features: Dict[str, float]) -> Tuple[RegimeLabel, float]:
        """Classify regime based on extracted features."""
        atr_r = features["atr_ratio"]
        slope = abs(features["norm_slope"])
        er = features["efficiency_ratio"]
        vol_r = features["vol_ratio"]

        # News Shock: Extreme volatility spike
        if atr_r > 2.5 or vol_r > 2.5:
            return RegimeLabel.NEWS_SHOCK, min(0.9, (atr_r + vol_r) / 10)

        # Volatile Breakout: High volatility and strong trend efficiency
        if atr_r > 1.5 and er > 0.6:
            return RegimeLabel.VOLATILE_BREAKOUT, min(0.85, er)

        # Trending: Moderate volatility, high efficiency ratio
        if er > 0.3 and slope > 0.01:
            return RegimeLabel.TRENDING, min(0.8, er * 1.5)

        # Low Volatility Drift: Low volatility, but consistent slope
        if atr_r < 0.8 and slope > 0.005:
            return RegimeLabel.LOW_VOLATILITY_DRIFT, 0.7

        # Mean Reversion: High volatility but low efficiency (oscillating)
        if atr_r > 1.2 and er < 0.2:
            return RegimeLabel.MEAN_REVERSION, 0.75

        # Default: Ranging
        return RegimeLabel.RANGING, 0.6

    def _calculate_transition_score(self, df: pd.DataFrame) -> float:
        """Calculate probability of imminent regime transition."""
        # Simple proxy: Rate of change of volatility
        close = df["close"]
        returns = close.pct_change()
        vol = returns.rolling(window=10).std()
        vol_roc = vol.pct_change().abs().iloc[-1]

        # Cap at 1.0
        return float(min(1.0, vol_roc * 5))

    def get_historical_regimes(self, df: pd.DataFrame) -> pd.Series:
        """
        Label historical data with regimes.

        Args:
            df: DataFrame with OHLCV data.

        Returns:
            Series of regime labels.
        """
        regimes = []
        # Pre-calculate to avoid redundant overhead if possible,
        # but for simplicity we iterate with a sliding window
        for i in range(len(df)):
            if i < self.volatility_window:
                regimes.append(RegimeLabel.RANGING.value)
                continue

            sub_df = df.iloc[i - self.volatility_window + 1 : i + 1]
            regime = self.detect(sub_df)
            regimes.append(regime.label.value)

        return pd.Series(regimes, index=df.index)

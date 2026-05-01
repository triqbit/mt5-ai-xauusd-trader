"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection system for XAUUSD.
Classifies market state into: trending, ranging, volatile breakout,
low-volatility drift, news shock, and mean-reversion.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"

class RegimeInfo(BaseModel):
    """
    Typed regime object for system-wide consumption.
    """
    label: MarketRegime = Field(..., description="The detected market regime label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the detection")
    transition_score: float = Field(..., ge=0.0, le=1.0, description="Score indicating probability of regime transition")
    metadata: Dict[str, float] = Field(default_factory=dict, description="Additional metrics used for detection")

class RegimeDetector:
    """
    Adaptive market-state layer using statistical features and ATR behavior.
    """
    def __init__(self, window: int = 20, long_window: int = 100):
        self.window = window
        self.long_window = long_window

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate statistical features for regime detection.
        """
        df = df.copy()

        # 1. True Range and ATR
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=self.window).mean()
        df["atr_long"] = tr.rolling(window=self.long_window).mean()
        df["atr_ratio"] = df["atr"] / (df["atr_long"] + 1e-9)

        # 2. Returns and Volatility
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].rolling(window=self.window).std()
        df["vol_ratio"] = df["volatility"] / (df["returns"].rolling(window=self.long_window).std() + 1e-9)

        # 3. Efficiency Ratio (Kaufman)
        net_change = (df["close"] - df["close"].shift(self.window)).abs()
        sum_changes = (df["close"] - df["close"].shift(1)).abs().rolling(window=self.window).sum()
        df["efficiency_ratio"] = net_change / (sum_changes + 1e-9)

        # 4. Slope (Linear Regression)
        def get_slope(y):
            x = np.arange(len(y))
            # y is a numpy array here when called by rolling.apply
            return np.polyfit(x, y, 1)[0] / (y[0] + 1e-9)

        df["slope"] = df["close"].rolling(window=self.window).apply(get_slope, raw=True)

        # 5. Price Z-score (Relative to MA)
        ma = df["close"].rolling(window=self.window).mean()
        std = df["close"].rolling(window=self.window).std()
        df["z_score"] = (df["close"] - ma) / (std + 1e-9)

        return df

    def _classify_row(self, row: pd.Series | Dict[str, Any]) -> Tuple[MarketRegime, float]:
        """
        Core classification logic shared between detect and label_history.
        """
        label = MarketRegime.RANGING
        confidence = 0.5

        z_score = row["z_score"]
        atr_ratio = row["atr_ratio"]
        efficiency_ratio = row["efficiency_ratio"]
        slope = row["slope"]

        # 1. News Shock: Massive price move relative to volatility
        if abs(z_score) > 3.0 or atr_ratio > 3.0:
            label = MarketRegime.NEWS_SHOCK
            confidence = min(abs(z_score) / 5.0, 1.0)

        # 2. Volatile Breakout: High efficiency + high ATR ratio
        elif efficiency_ratio > 0.6 and atr_ratio > 1.5:
            label = MarketRegime.VOLATILE_BREAKOUT
            confidence = min(efficiency_ratio, 1.0)

        # 3. Trending: High efficiency + consistent slope
        elif efficiency_ratio > 0.4 and abs(slope) > 0.0001:
            label = MarketRegime.TRENDING
            confidence = efficiency_ratio

        # 4. Low-Volatility Drift: Consistent slope but low ATR ratio
        elif abs(slope) > 0.00005 and atr_ratio < 1.0:
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 0.6

        # 5. Mean Reversion: Extreme Z-score but low efficiency
        elif abs(z_score) > 2.0 and efficiency_ratio < 0.3:
            label = MarketRegime.MEAN_REVERSION
            confidence = 0.7

        # 6. Ranging: Default if efficiency is low
        elif efficiency_ratio < 0.3:
            label = MarketRegime.RANGING
            confidence = 1.0 - efficiency_ratio

        return label, float(confidence)

    def detect(self, data: pd.DataFrame) -> RegimeInfo:
        """
        Detect current market regime from the latest data.
        """
        if len(data) < self.long_window:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0
            )

        features = self._calculate_features(data.tail(self.long_window + 1))
        latest = features.iloc[-1]

        label, confidence = self._classify_row(latest)

        # Simple transition score: change in efficiency ratio or volatility
        prev = features.iloc[-2]
        transition_score = abs(latest["efficiency_ratio"] - prev["efficiency_ratio"])
        transition_score = min(transition_score * 2, 1.0)

        return RegimeInfo(
            label=label,
            confidence=confidence,
            transition_score=float(transition_score),
            metadata={
                "efficiency_ratio": float(latest["efficiency_ratio"]),
                "atr_ratio": float(latest["atr_ratio"]),
                "slope": float(latest["slope"]),
                "z_score": float(latest["z_score"]),
                "vol_ratio": float(latest["vol_ratio"])
            }
        )

    def label_history(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply regime labeling to historical data.
        """
        if len(data) < self.long_window:
            df = data.copy()
            df["regime"] = MarketRegime.UNKNOWN.value
            return df

        features = self._calculate_features(data)

        regimes = [MarketRegime.UNKNOWN.value] * len(features)
        confidences = [0.0] * len(features)

        # Iterate over rows that have enough history
        # (Using itertuples or apply would be faster, let's use itertuples for safety and speed)
        for i in range(self.long_window, len(features)):
            row = features.iloc[i]
            label, confidence = self._classify_row(row)
            regimes[i] = label.value
            confidences[i] = confidence

        df = data.copy()
        df["regime"] = regimes
        df["regime_confidence"] = confidences
        df["efficiency_ratio"] = features["efficiency_ratio"]
        df["atr_ratio"] = features["atr_ratio"]
        df["z_score"] = features["z_score"]

        return df

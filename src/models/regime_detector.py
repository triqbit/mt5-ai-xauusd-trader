"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market state classification into regimes (Trending, Ranging, Volatile, etc.)
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class RegimeType(str, Enum):
    """Supported market regime types."""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class MarketRegime(BaseModel):
    """Typed market regime classification result."""
    model_config = ConfigDict(frozen=True)

    label: RegimeType
    confidence: float = Field(ge=0.0, le=1.0)
    transition_score: float = Field(default=0.0, description="Likelihood of regime change")
    features: Dict[str, float] = Field(default_factory=dict, description="Raw features used for detection")


class RegimeDetector:
    """
    Classifies market state into regimes using OHLCV-derived statistical features.

    Uses volatility (ATR), efficiency ratio, slope/angle, and price location
    relative to moving averages to determine the current market environment.
    """

    def __init__(
        self,
        window_size: int = 20,
        volatility_window: int = 14,
        trend_threshold: float = 0.4,
        volatility_threshold: float = 2.0,
    ) -> None:
        """
        Initialize the RegimeDetector.

        Args:
            window_size: Period for trend and efficiency calculations.
            volatility_window: Period for ATR calculation.
            trend_threshold: Minimum efficiency ratio to consider as trending.
            volatility_threshold: Multiple of rolling ATR to detect volatility spikes.
        """
        self.window_size = window_size
        self.volatility_window = volatility_window
        self.trend_threshold = trend_threshold
        self.volatility_threshold = volatility_threshold

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate statistical features from OHLCV data.
        """
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # 1. Volatility (ATR)
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=self.volatility_window).mean()

        # Volatility ratio (current ATR vs long-term mean ATR)
        long_term_atr = df["atr"].rolling(window=self.window_size * 5).mean()
        df["vol_ratio"] = df["atr"] / (long_term_atr + 1e-9)

        # 2. Trend (Efficiency Ratio & Slope)
        # Efficiency Ratio (Kaufman) = Net Change / Total Path
        net_change = (df["close"] - df["close"].shift(self.window_size)).abs()
        path = (df["close"] - df["close"].shift(1)).abs().rolling(window=self.window_size).sum()
        df["er"] = net_change / (path + 1e-9)

        df["sma"] = df["close"].rolling(window=self.window_size).mean()
        df["slope"] = (df["sma"] - df["sma"].shift(5)) / (df["sma"].shift(5) * 5 + 1e-9)

        # 3. Mean Reversion (Z-Score)
        rolling_std = df["close"].rolling(window=self.window_size).std()
        df["z_score"] = (df["close"] - df["sma"]) / (rolling_std + 1e-9)

        # 4. Acceleration (ATR expansion)
        df["atr_accel"] = df["atr"] / (df["atr"].shift(5) + 1e-9)

        return df

    def _classify_row(self, row: pd.Series) -> MarketRegime:
        """
        Apply heuristic rules to classify a single row of features.
        """
        er = row.get("er", 0)
        vol_ratio = row.get("vol_ratio", 1.0)
        z_score = abs(row.get("z_score", 0))
        atr_accel = row.get("atr_accel", 1.0)
        slope = abs(row.get("slope", 0))

        # Defaults
        label = RegimeType.UNKNOWN
        confidence = 0.5

        # 1. News Shock / Volatile Breakout (High ATR accel + high vol ratio)
        if atr_accel > self.volatility_threshold or vol_ratio > 2.5:
            if er > self.trend_threshold:
                label = RegimeType.VOLATILE_BREAKOUT
                confidence = min(0.6 + (atr_accel / 10), 0.95)
            else:
                label = RegimeType.NEWS_SHOCK
                confidence = min(0.7 + (vol_ratio / 10), 0.98)

        # 2. Trending (High Efficiency Ratio + moderate volatility)
        elif er > self.trend_threshold and vol_ratio < 2.0:
            label = RegimeType.TRENDING
            confidence = min(0.5 + er, 0.9)

        # 3. Mean Reversion (High Z-Score + Low/Med Volatility + Low Efficiency)
        elif z_score > 2.0 and er < self.trend_threshold:
            label = RegimeType.MEAN_REVERSION
            confidence = min(0.4 + (z_score / 10), 0.85)

        # 4. Low Volatility Drift (Low Volatility + Moderate Trend/Efficiency)
        elif vol_ratio < 0.8 and slope > 0.0001:
            label = RegimeType.LOW_VOLATILITY_DRIFT
            confidence = 0.7

        # 5. Ranging (Low Efficiency + Low Volatility Ratio)
        elif er < 0.2 and vol_ratio < 1.2:
            label = RegimeType.RANGING
            confidence = 0.6 + (0.2 - er)

        # Transition score calculation (heuristic)
        # Higher score if features are near thresholds or changing rapidly
        transition_score = (abs(er - self.trend_threshold) < 0.05) * 0.3 + (atr_accel > 1.5) * 0.4

        return MarketRegime(
            label=label,
            confidence=float(confidence),
            transition_score=float(min(transition_score, 1.0)),
            features={
                "er": float(er),
                "vol_ratio": float(vol_ratio),
                "z_score": float(row.get("z_score", 0)),
                "atr_accel": float(atr_accel)
            }
        )

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect the current market regime from the latest data.
        """
        if len(df) < self.window_size * 5:
            return MarketRegime(label=RegimeType.UNKNOWN, confidence=0.0)

        df_feat = self._calculate_features(df)
        latest = df_feat.iloc[-1]

        if pd.isna(latest["er"]) or pd.isna(latest["vol_ratio"]):
            return MarketRegime(label=RegimeType.UNKNOWN, confidence=0.0)

        return self._classify_row(latest)

    def label_historical(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply regime labeling to an entire historical dataset.
        """
        df_feat = self._calculate_features(df)
        regimes = []

        for _, row in df_feat.iterrows():
            if pd.isna(row["er"]) or pd.isna(row["vol_ratio"]):
                regimes.append(RegimeType.UNKNOWN.value)
            else:
                regimes.append(self._classify_row(row).label.value)

        df["regime"] = regimes
        return df

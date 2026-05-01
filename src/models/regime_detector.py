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
from typing import Optional

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
    """

    def __init__(self, window: int = 20, long_window: int = 100) -> None:
        self.window = window
        self.long_window = long_window
        self._last_regime: MarketRegime = MarketRegime.UNKNOWN

    def _calculate_efficiency_ratio(self, prices: np.ndarray) -> float:
        """Kaufman Efficiency Ratio: net change / sum of absolute changes."""
        if len(prices) < 2:
            return 0.0
        net_change = abs(prices[-1] - prices[0])
        abs_changes = np.abs(np.diff(prices))
        sum_abs_changes = np.sum(abs_changes)
        return float(net_change / sum_abs_changes) if sum_abs_changes > 0 else 0.0

    def _calculate_slope(self, prices: np.ndarray) -> float:
        """Normalized linear regression slope."""
        if len(prices) < 2:
            return 0.0
        x = np.arange(len(prices))
        y = prices
        # Use simple linear regression formula
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (
            n * np.sum(x**2) - (np.sum(x)) ** 2
        )
        # Normalize slope by price level
        return float(slope / prices[0])

    def detect(self, data: pd.DataFrame) -> RegimeInfo:
        """
        Detect current market regime from OHLCV data.
        Requires at least 'long_window' bars.
        """
        if len(data) < self.long_window:
            return RegimeInfo(
                label=MarketRegime.UNKNOWN,
                confidence=0.0,
                transition_score=0.0,
                volatility_index=0.0,
            )

        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        # 1. Volatility (ATR Ratio)
        def get_tr(h, l, c_prev):
            return max(h - l, abs(h - c_prev), abs(l - c_prev))

        tr = np.zeros(len(data))
        for i in range(1, len(data)):
            tr[i] = get_tr(high[i], low[i], close[i - 1])
        tr[0] = high[0] - low[0]

        atr_short = np.mean(tr[-self.window :])
        atr_long = np.mean(tr[-self.long_window :])
        atr_ratio = atr_short / atr_long if atr_long > 0 else 1.0

        # 2. Efficiency Ratio
        er = self._calculate_efficiency_ratio(close[-self.window :])

        # 3. Price Slope
        slope = self._calculate_slope(close[-self.window :])

        # 4. Z-Score (Distance from Mean)
        ma = np.mean(close[-self.window :])
        std = np.std(close[-self.window :]) + 1e-9
        z_score = abs(close[-1] - ma) / std

        # --- Regime Logic ---
        label = MarketRegime.RANGING
        confidence = 0.5

        if atr_ratio > 2.5 or (z_score > 3.0 and er > 0.8):
            label = MarketRegime.NEWS_SHOCK
            confidence = min(atr_ratio / 4.0, 1.0)
        elif er > 0.6 and abs(slope) > 0.0001:
            if atr_ratio > 1.5:
                label = MarketRegime.VOLATILE_BREAKOUT
            else:
                label = MarketRegime.TRENDING
            confidence = er
        elif z_score > 2.5 and er < 0.3:
            label = MarketRegime.MEAN_REVERSION
            confidence = min(z_score / 4.0, 1.0)
        elif abs(slope) > 0.00005 and atr_ratio < 0.8:
            label = MarketRegime.LOW_VOLATILITY_DRIFT
            confidence = 0.7
        else:
            label = MarketRegime.RANGING
            confidence = 1.0 - er

        # Transition score (change in ER or ATR ratio)
        transition_score = abs(atr_ratio - 1.0) * 0.5 + abs(er - 0.5)

        regime_info = RegimeInfo(
            label=label,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            transition_score=float(np.clip(transition_score, 0.0, 1.0)),
            volatility_index=float(atr_ratio),
        )

        if label != self._last_regime:
            logger.info("Regime transition: %s -> %s", self._last_regime, label)
            self._last_regime = label

        return regime_info

    def label_history(self, data: pd.DataFrame) -> pd.DataFrame:
        """Adds regime columns to historical DataFrame."""
        df = data.copy()
        regimes = []
        confidences = []

        # This is slow but robust for research
        for i in range(len(df)):
            if i < self.long_window:
                regimes.append(MarketRegime.UNKNOWN.value)
                confidences.append(0.0)
            else:
                info = self.detect(df.iloc[i - self.long_window + 1 : i + 1])
                regimes.append(info.label.value)
                confidences.append(info.confidence)

        df["regime"] = regimes
        df["regime_confidence"] = confidences
        return df

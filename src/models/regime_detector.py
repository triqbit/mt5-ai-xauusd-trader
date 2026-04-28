"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection and classification.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, Any, Optional

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RegimeType(str, Enum):
    TRENDING = "Trending"
    RANGING = "Ranging"
    VOLATILE_BREAKOUT = "Volatile Breakout"
    LOW_VOLATILITY_DRIFT = "Low Volatility Drift"
    NEWS_SHOCK = "News Shock"
    MEAN_REVERSION = "Mean Reversion"
    UNKNOWN = "Unknown"

class MarketRegime(BaseModel):
    """Structured detection results."""
    label: RegimeType
    confidence: float
    transition_score: float
    features: Dict[str, float]

class RegimeDetector:
    """
    Classifies market states based on price action and volatility metrics.
    Uses ATR, SMA slope, and Kaufman Efficiency Ratio.
    """

    def __init__(self, window: int = 20) -> None:
        self.window = window

    def detect(self, df_ohlcv: Any) -> MarketRegime:
        """
        Analyze OHLCV data to detect the current market regime.
        df_ohlcv: Pandas DataFrame with 'open', 'high', 'low', 'close', 'tick_volume'.
        """
        try:
            if len(df_ohlcv) < self.window:
                return self._unknown_regime()

            close = df_ohlcv["close"].values
            high = df_ohlcv["high"].values
            low = df_ohlcv["low"].values

            # 1. Kaufman Efficiency Ratio (ER)
            # ER = direction / volatility
            direction = abs(close[-1] - close[-self.window])
            volatility = np.sum(np.abs(np.diff(close[-(self.window + 1):])))
            er = direction / (volatility + 1e-9)

            # 2. SMA Slope (Normalised)
            sma = df_ohlcv["close"].rolling(self.window).mean().values
            slope = (sma[-1] - sma[-5]) / (sma[-5] + 1e-9) if len(sma) >= 5 else 0.0

            # 3. ATR and ATR Acceleration
            tr = np.maximum(high - low, np.maximum(abs(high - np.roll(close, 1)), abs(low - np.roll(close, 1))))
            atr = np.mean(tr[-self.window:])
            prev_atr = np.mean(tr[-self.window*2:-self.window]) if len(tr) >= self.window*2 else atr
            atr_accel = (atr - prev_atr) / (prev_atr + 1e-9)

            # 4. Price Z-Score
            mean = np.mean(close[-self.window:])
            std = np.std(close[-self.window:]) + 1e-9
            z_score = (close[-1] - mean) / std

            features = {
                "efficiency_ratio": float(er),
                "sma_slope": float(slope),
                "atr": float(atr),
                "atr_accel": float(atr_accel),
                "z_score": float(z_score),
            }

            # Classification Logic
            label = RegimeType.RANGING
            confidence = 0.5

            if atr_accel > 0.5 and er > 0.6:
                label = RegimeType.VOLATILE_BREAKOUT
                confidence = 0.8
            elif er > 0.7:
                label = RegimeType.TRENDING
                confidence = 0.85
            elif er < 0.2 and abs(z_score) < 1.0:
                label = RegimeType.LOW_VOLATILITY_DRIFT
                confidence = 0.7
            elif abs(z_score) > 2.5:
                label = RegimeType.NEWS_SHOCK
                confidence = 0.9
            elif er < 0.3 and abs(z_score) > 1.5:
                label = RegimeType.MEAN_REVERSION
                confidence = 0.75
            else:
                label = RegimeType.RANGING
                confidence = 0.6

            return MarketRegime(
                label=label,
                confidence=confidence,
                transition_score=0.1,  # Placeholder
                features=features
            )

        except Exception as exc:
            logger.error("Regime detection failed: %s", exc)
            return self._unknown_regime()

    def _unknown_regime(self) -> MarketRegime:
        return MarketRegime(
            label=RegimeType.UNKNOWN,
            confidence=0.0,
            transition_score=0.0,
            features={}
        )

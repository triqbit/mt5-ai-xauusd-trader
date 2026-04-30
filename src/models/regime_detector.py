"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/regime_detector.py
Market regime detection system to classify price action into:
Trending, Ranging, Volatile Breakout, Low-Volatility Drift, News Shock, Mean-Reversion.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RegimeType(str, Enum):
    """Supported market regimes."""
    TRENDING = "Trending"
    RANGING = "Ranging"
    VOLATILE_BREAKOUT = "Volatile Breakout"
    LOW_VOLATILITY_DRIFT = "Low-Volatility Drift"
    NEWS_SHOCK = "News Shock"
    MEAN_REVERSION = "Mean-Reversion"
    UNKNOWN = "Unknown"


class MarketRegime(BaseModel):
    """Strongly-typed market regime object."""
    type: RegimeType
    confidence: float
    transition_score: float = 0.0
    volatility_ratio: float = 1.0
    trend_angle: float = 0.0


class RegimeDetector:
    """
    Heuristic and ML-based market regime classification.
    """

    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size

    def detect(self, prices: np.ndarray, volumes: Optional[np.ndarray] = None) -> MarketRegime:
        """
        Analyze recent price action to determine the current regime.
        Simplistic implementation for support of explainability.
        """
        if len(prices) < self.window_size:
            return MarketRegime(type=RegimeType.UNKNOWN, confidence=0.0)

        recent = prices[-self.window_size:]

        # Calculate basic metrics
        returns = np.diff(recent)
        volatility = np.std(returns)
        hist_volatility = np.std(np.diff(prices)) if len(prices) > self.window_size else volatility

        vol_ratio = volatility / (hist_volatility + 1e-9)

        # Trend detection (linear regression slope)
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)

        # Regime logic
        if vol_ratio > 2.0:
            rtype = RegimeType.NEWS_SHOCK
            conf = min(vol_ratio / 4.0, 1.0)
        elif abs(slope) > (np.mean(recent) * 0.001):
            rtype = RegimeType.TRENDING
            conf = 0.8
        elif vol_ratio < 0.5:
            rtype = RegimeType.LOW_VOLATILITY_DRIFT
            conf = 0.7
        else:
            rtype = RegimeType.RANGING
            conf = 0.6

        return MarketRegime(
            type=rtype,
            confidence=conf,
            volatility_ratio=vol_ratio,
            trend_angle=float(np.arctan(slope))
        )

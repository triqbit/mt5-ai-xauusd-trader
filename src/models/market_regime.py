"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/market_regime.py
Centralized Enum for market regimes.
Author : triqbit
License: MIT
"""
from enum import Enum


class MarketRegime(Enum):
    """
    Institutional classification of market states for XAUUSD.
    """
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE_BREAKOUT = "VOLATILE_BREAKOUT"
    LOW_VOL_DRIFT = "LOW_VOL_DRIFT"
    NEWS_SHOCK = "NEWS_SHOCK"
    MEAN_REVERSION = "MEAN_REVERSION"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value

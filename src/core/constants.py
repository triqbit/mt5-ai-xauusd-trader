"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/constants.py
Centralized enums and constants for system-wide consistency.
Author : triqbit
License: MIT
"""

from enum import Enum, IntEnum


class SignalDirection(IntEnum):
    """Standardized signal directions."""

    BUY = 1
    SELL = -1
    HOLD = 0


class ModelAction(IntEnum):
    """Actions produced by ML/RL models (XAUUSD-Optimized Index)."""

    BUY = 0
    SELL = 1
    HOLD = 2


class MarketRegime(str, Enum):
    """XAUUSD Market Regimes."""

    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    LOW_VOLATILITY_DRIFT = "low_volatility_drift"
    NEWS_SHOCK = "news_shock"
    MEAN_REVERSION = "mean_reversion"
    UNKNOWN = "unknown"


class SymbolContractSize(IntEnum):
    """Contract sizes for various symbols."""

    XAUUSD = 100
    XAGUSD = 5000
    EURUSD = 100000
    GBPUSD = 100000
    USDJPY = 100000
    USDCHF = 100000
    AUDUSD = 100000
    EURJPY = 100000

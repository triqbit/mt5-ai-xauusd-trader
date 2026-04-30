"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Typed exceptions for the trading bot to enable structured recovery flows.
"""

class TradingBotError(Exception):
    """Base exception for all trading bot related errors."""
    pass

class MT5ConnectionError(TradingBotError):
    """Raised when connection to MT5 terminal or MetaAPI fails."""
    pass

class MarketDataError(TradingBotError):
    """Raised when fetching OHLCV or tick data fails."""
    pass

class OrderExecutionError(TradingBotError):
    """Raised when an order placement or modification fails."""
    pass

class RiskValidationError(TradingBotError):
    """Raised when a signal fails risk management validation."""
    pass

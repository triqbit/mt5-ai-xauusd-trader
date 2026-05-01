"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Centralised typed exception hierarchy for structured error handling.
Author : triqbit
License: MIT
"""


class TradingBotError(Exception):
    """Base class for all exceptions in the trading bot."""

    pass


class MT5Error(TradingBotError):
    """Base class for all MetaTrader 5 related errors."""

    pass


class MT5ConnectionError(MT5Error):
    """Raised when connection to MT5 terminal or MetaAPI fails."""

    pass


class MT5DataError(MT5Error):
    """Raised when fetching market data from MT5 fails."""

    pass


class RiskValidationError(TradingBotError):
    """Raised when a trade signal fails risk validation."""

    pass


class OrderExecutionError(TradingBotError):
    """Raised when an order cannot be placed or executed."""

    pass

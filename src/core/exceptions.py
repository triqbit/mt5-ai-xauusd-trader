"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Typed exception hierarchy for structured error handling.
Author : triqbit
License: MIT
"""

class BotError(Exception):
    """Base exception for all bot-related errors."""
    pass

class MT5Error(BotError):
    """Base exception for MetaTrader 5 related errors."""
    pass

class MT5ConnectionError(MT5Error):
    """Raised when connection to MT5 terminal or MetaAPI fails."""
    pass

class MT5DataError(MT5Error):
    """Raised when fetching data (rates, ticks, account info) from MT5 fails."""
    pass

class OrderExecutionError(MT5Error):
    """Raised when an order placement or modification fails."""
    pass

class RiskValidationError(BotError):
    """Raised when a trade signal fails risk management validation."""
    pass

class ConfigurationError(BotError):
    """Raised when there is an issue with the bot configuration."""
    pass

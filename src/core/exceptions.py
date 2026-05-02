"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Typed exception hierarchy for structured error handling and recovery.
Author : triqbit
License: MIT
"""

class BotError(Exception):
    """Base class for all bot-related exceptions."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}

class MT5Error(BotError):
    """Base class for MetaTrader 5 related errors."""
    pass

class MT5ConnectionError(MT5Error):
    """Raised when connection to MT5 terminal or MetaAPI fails."""
    pass

class MT5DataError(MT5Error):
    """Raised when market data retrieval fails."""
    pass

class OrderExecutionError(MT5Error):
    """Raised when an order fails to execute."""
    pass

class RiskValidationError(BotError):
    """Raised when a signal fails risk validation checks."""
    pass

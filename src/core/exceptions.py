"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Typed exception hierarchy for structured error handling.
"""

class TraderError(Exception):
    """Base class for all exceptions in the trader application."""
    pass

class MT5ConnectionError(TraderError):
    """Raised when there is an issue connecting to MetaTrader 5."""
    pass

class RiskValidationError(TraderError):
    """Raised when a trade signal fails risk management validation."""
    pass

class MarketDataError(TraderError):
    """Raised when there is an issue fetching or processing market data."""
    pass

class OrderExecutionError(TraderError):
    """Raised when an order fails to execute."""
    pass

class ConfigurationError(TraderError):
    """Raised when there is a configuration error."""
    pass

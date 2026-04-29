"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Custom exception hierarchy for granular error handling.
"""

class TradingBotError(Exception):
    """Base exception for all trading bot errors."""
    pass

class MT5Error(TradingBotError):
    """Base exception for MetaTrader 5 related errors."""
    pass

class MT5ConnectionError(MT5Error):
    """Raised when connection to MT5 terminal or MetaAPI fails."""
    pass

class MT5DataError(MT5Error):
    """Raised when fetching market data (rates, ticks) fails."""
    pass

class MT5ExecutionError(MT5Error):
    """Raised when order execution or management fails."""
    pass

class RiskManagerError(TradingBotError):
    """Raised when risk management logic encounters a critical failure."""
    pass

class ConfigurationError(TradingBotError):
    """Raised when there is an error in the bot configuration."""
    pass

class CircuitBreakerError(TradingBotError):
    """Raised when an operation is blocked by an open circuit breaker."""
    pass

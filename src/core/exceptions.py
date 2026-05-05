from __future__ import annotations

from typing import Any

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Centralized exception hierarchy for robust error handling and recovery.
"""

class TradingError(Exception):
    """
    Base exception for all trading-related errors in the system.
    Provides a dictionary for carrying extra contextual metadata about the failure.
    """
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class MT5Error(TradingError):
    """
    Base exception for all MetaTrader 5 (MT5) specific failures.
    Covers both native SDK and MetaAPI cloud path issues.
    """
    pass


class MT5ConnectionError(MT5Error):
    """
    Raised when connection to the MT5 terminal or MetaAPI cloud gateway fails.
    This usually triggers reconnection logic in the main trading loop.
    """
    pass


class MT5DataError(MT5Error):
    """
    Raised when market data retrieval (OHLCV rates, ticks) from MT5 fails.
    Often indicates a transient network issue or an unsubscribed symbol.
    """
    pass


class MT5ExecutionError(MT5Error):
    """
    Raised when order execution (buy/sell) or position management fails.
    Contains MT5 return codes in details if available.
    """
    pass


class ConfigurationError(TradingError):
    """
    Raised when the system detects invalid or missing startup configuration.
    Usually caught by the ConfigValidator during the bootstrap process.
    """
    pass


class RiskValidationError(TradingError):
    """
    Raised when a trade signal fails the strict Pydantic schema validation.
    Ensures malformed signals are caught before reaching the risk engine.
    """
    pass

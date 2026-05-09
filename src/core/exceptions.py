from __future__ import annotations

from typing import Any

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/exceptions.py
Centralized exception hierarchy for robust error handling and recovery.
"""


class TradingError(Exception):
    """Base exception for all trading-related errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        is_retriable: bool = True,
    ):
        super().__init__(message)
        self.details = details or {}
        self.is_retriable = is_retriable


class MT5Error(TradingError):
    """Base exception for MetaTrader 5 related errors."""

    pass


class MT5ConnectionError(MT5Error):
    """Raised when connection to MT5 terminal or MetaAPI fails."""

    pass


class MT5DataError(MT5Error):
    """Raised when data retrieval (rates, ticks) from MT5 fails."""

    pass


class MT5ExecutionError(MT5Error):
    """Raised when order execution or management fails."""

    pass


class ConfigurationError(TradingError):
    """Raised when there is an issue with the system configuration."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details=details, is_retriable=False)


class CircuitBreakerError(TradingError):
    """Raised when an operation is blocked by an open circuit breaker."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, details=details, is_retriable=False)

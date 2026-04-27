"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/error_handler.py
Error handling, recovery, and circuit breaker system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import functools
import logging
import time
import traceback
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, Union

import structlog

from src.core.trade_logger import TradeLogger

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern to protect external API calls.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if (
                    self.last_failure_time
                    and (datetime.now() - self.last_failure_time).total_seconds()
                    > self.recovery_timeout
                ):
                    logger.info("Circuit breaker HALF_OPEN", name=self.name)
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError(f"Circuit breaker {self.name} is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exceptions as e:
                self._on_failure(e)
                raise

        return wrapper

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker CLOSED", name=self.name)
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        logger.warning(
            "Circuit breaker failure",
            name=self.name,
            failure_count=self.failure_count,
            error=str(exc),
        )

        if self.failure_count >= self.failure_threshold:
            logger.error("Circuit breaker OPEN", name=self.name)
            self.state = CircuitState.OPEN


def retry_with_backoff(
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
) -> Callable:
    """
    Decorator for exponential backoff retries.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for i in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if i == retries:
                        break
                    logger.warning(
                        "Retry failed, backing off",
                        func=func.__name__,
                        attempt=i + 1,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
            raise last_exc  # type: ignore

        return wrapper

    return decorator


class ErrorHandler:
    """
    Centralized error handler for the trading bot.
    Manages DLQ, structured logging, and graceful degradation.
    """

    def __init__(self, trade_logger: Optional[TradeLogger] = None) -> None:
        self.trade_logger = trade_logger
        self.fallbacks: Dict[str, Callable] = {}

    def register_fallback(self, name: str, fallback_func: Callable) -> None:
        """Register a fallback function for a given operation name."""
        self.fallbacks[name] = fallback_func

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        event_type: str = "UNHANDLED_ERROR",
        payload: Optional[Any] = None,
        can_retry: bool = False,
    ) -> Any:
        """
        Handle an error by logging it, sending to DLQ, and attempting recovery or fallback.
        """
        correlation_id = str(uuid.uuid4())
        ctx = context or {}
        ctx["correlation_id"] = correlation_id
        ctx["error"] = str(error)
        ctx["event_type"] = event_type

        # 1. Structured Logging
        logger.error("Error encountered", **ctx)
        logger.debug("Stack trace", stack_trace=traceback.format_exc(), correlation_id=correlation_id)

        # 2. Dead Letter Queue
        if self.trade_logger:
            try:
                import json

                payload_str = json.dumps(payload) if payload else "{}"
                self.trade_logger.log_dead_letter(
                    event_type=event_type,
                    payload=payload_str,
                    error_message=str(error),
                    stack_trace=traceback.format_exc(),
                    correlation_id=correlation_id,
                )
            except Exception as e:
                logger.error("Failed to log to DLQ", dlq_error=str(e), original_correlation_id=correlation_id)

        # 3. Graceful Degradation / Fallback
        fallback = self.fallbacks.get(event_type)
        if fallback:
            logger.info("Executing fallback", event_type=event_type, correlation_id=correlation_id)
            try:
                return fallback()
            except Exception as fe:
                logger.error("Fallback failed", fallback_error=str(fe), correlation_id=correlation_id)

        return None

    def wrap_with_fallback(self, name: str, fallback_result: Any = None) -> Callable:
        """Decorator to wrap a function with a fallback in case of failure."""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.handle_error(
                        error=e,
                        event_type=name,
                        context={"func": func.__name__},
                    )
                    return fallback_result

            return wrapper

        return decorator

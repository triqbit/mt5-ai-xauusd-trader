"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/error_handler.py
Robust error handling, circuit breakers, and recovery systems.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import functools
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern.
    Transitions: CLOSED -> OPEN (on failure threshold) -> HALF_OPEN (after timeout) -> CLOSED (on success)
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open", name=self.name)
            else:
                raise RuntimeError(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("circuit_breaker_closed", name=self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self, exception: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            failure_count=self.failure_count,
            state=self.state.value,
            error=str(exception)
        )

        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error("circuit_breaker_opened", name=self.name, error=str(exception))

def exponential_backoff(
    retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for exponential backoff retries.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        "retry_attempt",
                        func=func.__name__,
                        attempt=attempt + 1,
                        retries=retries,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
            raise last_exception or RuntimeError("Maximum retries reached")
        return wrapper
    return decorator

class ErrorHandler:
    """
    Unified error handler for structured logging and recovery actions.
    """
    def __init__(self, trade_logger: Optional[Any] = None):
        self.trade_logger = trade_logger
        self.context: Dict[str, Any] = {}

    def with_context(self, **kwargs) -> ErrorHandler:
        """Add persistent context to subsequent logs."""
        self.context.update(kwargs)
        if "correlation_id" not in self.context:
            self.context["correlation_id"] = str(uuid.uuid4())
        return self

    def handle_error(
        self,
        error: Exception,
        severity: str = "ERROR",
        action: Optional[str] = None,
        dlq_event: Optional[Dict[str, Any]] = None
    ):
        """
        Log error with context and optionally send to Dead Letter Queue (DLQ).
        """
        log_method = getattr(logger, severity.lower(), logger.error)
        log_method(
            "error_occurred",
            error=str(error),
            error_type=type(error).__name__,
            action=action,
            **self.context
        )

        if dlq_event and self.trade_logger:
            try:
                self.trade_logger.log_dead_letter(
                    event_type=dlq_event.get("type", "UNKNOWN"),
                    payload=dlq_event.get("payload", {}),
                    error_message=str(error),
                    correlation_id=self.context.get("correlation_id")
                )
                logger.info("event_sent_to_dlq", correlation_id=self.context.get("correlation_id"))
            except Exception as e:
                logger.critical("failed_to_log_to_dlq", error=str(e))

    @staticmethod
    def get_correlation_id() -> str:
        return str(uuid.uuid4())

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/error_handler.py
Resilience utilities: Circuit Breaker and Retry with Backoff.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import functools
import random
import time
from enum import Enum
from typing import Any, Callable, Optional, Type, Union

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Exception raised when the circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation to prevent cascading failures.
    States:
      - CLOSED: Normal operation, requests pass through.
      - OPEN: Failures exceeded threshold, requests are blocked.
      - HALF_OPEN: Recovery period elapsed, testing if service is back.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function through the circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open", name=self.name)
            else:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures = 0
                logger.info("circuit_breaker_closed", name=self.name)
            return result
        except Exception as e:
            self._handle_failure(e)
            raise e

    def _handle_failure(self, error: Exception) -> None:
        """Record a failure and transition state if threshold is reached."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "circuit_breaker_opened",
                name=self.name,
                failures=self.failures,
                error=str(error),
            )

    def decorate(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for easy application to methods."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(func, *args, **kwargs)

        return wrapper


def retry_with_backoff(
    retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
) -> Callable[..., Any]:
    """
    Decorator for exponential backoff retries.
    Args:
        retries: Maximum number of retry attempts.
        initial_delay: Delay before the first retry in seconds.
        exponential_base: Multiplier for subsequent retries.
        jitter: If True, adds random noise to delay.
        exceptions: Exception type(s) to catch and retry.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt > retries:
                        logger.error(
                            "retry_limit_reached",
                            func=func.__name__,
                            retries=retries,
                            error=str(e),
                        )
                        raise e

                    delay = initial_delay * (exponential_base ** (attempt - 1))
                    if jitter:
                        delay += random.uniform(0, 0.1 * delay)

                    logger.warning(
                        "retry_attempt",
                        func=func.__name__,
                        attempt=attempt,
                        delay=round(delay, 2),
                        error=str(e),
                    )
                    time.sleep(delay)

        return wrapper

    return decorator

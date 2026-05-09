"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/resilience.py
Robust Circuit Breaker pattern for graceful failure and self-healing.
"""

import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, Type

from src.core.exceptions import CircuitBreakerError

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Failing, requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern.
    Transitions:
    CLOSED -> OPEN: After failure_threshold is reached.
    OPEN -> HALF_OPEN: After recovery_timeout has passed.
    HALF_OPEN -> CLOSED: After a successful call.
    HALF_OPEN -> OPEN: After a single failed call.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions or (Exception,)

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Determines the current state based on failures and timeout."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time
            and (time.time() - self._last_failure_time) > self.recovery_timeout
        ):
            logger.info(
                "Circuit Breaker [%s] transitioning OPEN -> HALF_OPEN due to timeout.",
                self.name,
            )
            self._state = CircuitState.HALF_OPEN
        return self._state

    def _handle_success(self):
        """Reset the breaker on success."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info(
                "Circuit Breaker [%s] transitioning HALF_OPEN -> CLOSED after successful test.",
                self.name,
            )
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    def _handle_failure(self, exception: Exception):
        """Record a failure and trip the breaker if threshold reached."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.error(
                    "Circuit Breaker [%s] TRIPPED! State -> OPEN. (Failures: %d, Error: %s)",
                    self.name,
                    self._failure_count,
                    exception,
                )
            self._state = CircuitState.OPEN

    def __call__(self, func: Callable):
        """Decorator for circuit breaker integration."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                wait_time = self.recovery_timeout - (time.time() - (self._last_failure_time or 0))
                raise CircuitBreakerError(
                    f"Circuit Breaker [{self.name}] is OPEN. Blocked call to {func.__name__}.",
                    details={"wait_time_remaining": max(0, wait_time)},
                )

            try:
                result = func(*args, **kwargs)
                self._handle_success()
                return result
            except self.expected_exceptions as e:
                # If the exception is marked as non-retriable in our system, we might still want it to count
                # toward circuit breaking if it indicates a system-level failure (like connection loss).
                self._handle_failure(e)
                raise

        return wrapper

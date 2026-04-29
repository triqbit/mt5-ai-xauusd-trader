"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/error_handler.py
Implementation of Circuit Breaker pattern for resilience.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from src.core.exceptions import CircuitBreakerError

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Implementation of the Circuit Breaker pattern.
    Transitions:
    CLOSED -> OPEN: after 'failure_threshold' consecutive failures.
    OPEN -> HALF_OPEN: after 'recovery_timeout' seconds.
    HALF_OPEN -> CLOSED: after 'success_threshold' consecutive successes.
    HALF_OPEN -> OPEN: after a single failure.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes the decorated function if the circuit is not open.
        """
        self._check_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f"Circuit Breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._handle_success()
            return result
        except Exception as e:
            self._handle_failure(e)
            raise

    def _check_state(self):
        """Checks if the circuit should move from OPEN to HALF_OPEN."""
        if self.state == CircuitState.OPEN and self.last_failure_time:
            if (time.time() - self.last_failure_time) >= self.recovery_timeout:
                logger.info("Circuit Breaker '%s' transitioning to HALF_OPEN", self.name)
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0

    def _handle_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit Breaker '%s' transitioning to CLOSED", self.name)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _handle_failure(self, exception: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            "Circuit Breaker '%s' failure %d/%d: %s",
            self.name, self.failure_count, self.failure_threshold, exception
        )

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error("Circuit Breaker '%s' transitioning to OPEN", self.name)
                self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            logger.error("Circuit Breaker '%s' (HALF_OPEN) failed, transitioning back to OPEN", self.name)
            self.state = CircuitState.OPEN

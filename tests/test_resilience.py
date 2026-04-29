"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_resilience.py
Tests for Circuit Breaker and Error Handling logic.
"""

import time
import pytest
from unittest.mock import MagicMock
from src.core.error_handler import CircuitBreaker, CircuitState
from src.core.exceptions import CircuitBreakerError

def test_circuit_breaker_transitions():
    """Test CLOSED -> OPEN -> HALF_OPEN -> CLOSED transitions."""
    cb = CircuitBreaker("Test-CB", failure_threshold=2, recovery_timeout=1, success_threshold=1)

    # Starts CLOSED
    assert cb.state == CircuitState.CLOSED

    def failing_func():
        raise ValueError("Fail")

    def success_func():
        return "OK"

    # First failure
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Second failure -> OPEN
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    # Call while OPEN should raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        cb.call(success_func)

    # Wait for recovery timeout
    time.sleep(1.1)

    # First call after timeout -> HALF_OPEN -> CLOSED (because success_threshold=1)
    result = cb.call(success_func)
    assert result == "OK"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

def test_circuit_breaker_half_open_failure():
    """Test HALF_OPEN -> OPEN on failure."""
    cb = CircuitBreaker("Test-CB", failure_threshold=1, recovery_timeout=0.1, success_threshold=2)

    def failing_func():
        raise ValueError("Fail")

    # Transition to OPEN
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    time.sleep(0.2)

    # Transitions to HALF_OPEN on call, but fails -> OPEN
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

def test_circuit_breaker_half_open_success_threshold():
    """Test that multiple successes are required in HALF_OPEN if success_threshold > 1."""
    cb = CircuitBreaker("Test-CB", failure_threshold=1, recovery_timeout=0.1, success_threshold=2)

    def success_func():
        return "OK"

    def failing_func():
        raise ValueError("Fail")

    # CLOSED -> OPEN
    with pytest.raises(ValueError):
        cb.call(failing_func)

    time.sleep(0.2)

    # HALF_OPEN (1st success)
    cb.call(success_func)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1

    # HALF_OPEN -> CLOSED (2nd success)
    cb.call(success_func)
    assert cb.state == CircuitState.CLOSED
    assert cb.success_count == 0

import time
import pytest
from src.core.error_handler import CircuitBreaker, CircuitState, retry_with_backoff, ErrorHandler

def test_circuit_breaker_states():
    breaker = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

    @breaker
    def failing_func():
        raise ValueError("fail")

    @breaker
    def succeeding_func():
        return "ok"

    # Initially CLOSED
    assert breaker.state == CircuitState.CLOSED

    # First failure
    with pytest.raises(ValueError):
        failing_func()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 1

    # Second failure -> OPEN
    with pytest.raises(ValueError):
        failing_func()
    assert breaker.state == CircuitState.OPEN

    # Try calling when OPEN
    with pytest.raises(RuntimeError) as exc:
        succeeding_func()
    assert "is OPEN" in str(exc.value)

    # Wait for recovery timeout
    time.sleep(1.1)

    # Next call should be HALF_OPEN
    assert succeeding_func() == "ok"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

def test_retry_with_backoff():
    attempts = 0

    @retry_with_backoff(retries=2, initial_delay=0.1)
    def flappy_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("try again")
        return "success"

    assert flappy_func() == "success"
    assert attempts == 3

def test_error_handler_fallback():
    handler = ErrorHandler()

    def my_fallback():
        return "fallback_val"

    handler.register_fallback("TEST_EVENT", my_fallback)

    result = handler.handle_error(ValueError("oops"), event_type="TEST_EVENT")
    assert result == "fallback_val"

def test_wrap_with_fallback():
    handler = ErrorHandler()

    @handler.wrap_with_fallback(name="FUNC_ERROR", fallback_result="safe")
    def risky_func():
        raise RuntimeError("boom")

    assert risky_func() == "safe"

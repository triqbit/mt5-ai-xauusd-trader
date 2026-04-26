
import pytest
import time
from src.core.error_handler import CircuitBreaker, exponential_backoff, ErrorHandler, CircuitState

def test_circuit_breaker_threshold():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=1)

    def failing_func():
        raise ValueError("fail")

    # First failure
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # Second failure - should open
    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

    # Subsequent calls while open
    with pytest.raises(RuntimeError) as exc:
        cb.call(failing_func)
    assert "is OPEN" in str(exc.value)

def test_circuit_breaker_recovery():
    cb = CircuitBreaker(name="test_cb", failure_threshold=1, recovery_timeout=0.1)

    def failing_func():
        raise ValueError("fail")

    def success_func():
        return "ok"

    with pytest.raises(ValueError):
        cb.call(failing_func)
    assert cb.state == CircuitState.OPEN

    time.sleep(0.2)

    # Should transition to HALF_OPEN and then CLOSED on success
    assert cb.call(success_func) == "ok"
    assert cb.state == CircuitState.CLOSED

def test_exponential_backoff(mocker):
    mock_sleep = mocker.patch("time.sleep")

    attempts = 0
    def failing_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("retry")
        return "success"

    decorated = exponential_backoff(retries=5, base_delay=0.1)(failing_func)
    assert decorated() == "success"
    assert attempts == 3
    assert mock_sleep.call_count == 2

def test_error_handler_dlq(mocker):
    mock_logger = mocker.Mock()
    handler = ErrorHandler(trade_logger=mock_logger)

    error = ValueError("dead letter test")
    handler.handle_error(
        error,
        dlq_event={"type": "TEST_EVENT", "payload": {"data": 123}}
    )

    assert mock_logger.log_dead_letter.called
    args, kwargs = mock_logger.log_dead_letter.call_args
    assert kwargs["event_type"] == "TEST_EVENT"
    assert "dead letter test" in kwargs["error_message"]

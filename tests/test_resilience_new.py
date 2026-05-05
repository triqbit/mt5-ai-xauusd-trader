import pytest
from unittest.mock import MagicMock
from src.core.retry import with_retry
from src.core.exceptions import MT5Error, MT5ExecutionError

def test_retry_if_retriable_true():
    mock_func = MagicMock(side_effect=[
        MT5ExecutionError("transient", retriable=True),
        "success"
    ])

    @with_retry(MT5ExecutionError, retry_if=lambda e: getattr(e, "retriable", False), max_retries=2, initial_delay=0.01)
    def call_me():
        return mock_func()

    assert call_me() == "success"
    assert mock_func.call_count == 2

def test_retry_if_retriable_false():
    mock_func = MagicMock(side_effect=[
        MT5ExecutionError("permanent", retriable=False),
        "success"
    ])

    @with_retry(MT5ExecutionError, retry_if=lambda e: getattr(e, "retriable", False), max_retries=2, initial_delay=0.01)
    def call_me():
        return mock_func()

    with pytest.raises(MT5ExecutionError) as exc:
        call_me()

    assert "permanent" in str(exc.value)
    assert mock_func.call_count == 1

def test_retry_if_none_always_retries():
    # Backward compatibility check
    mock_func = MagicMock(side_effect=[
        ValueError("fail"),
        "success"
    ])

    @with_retry(ValueError, max_retries=2, initial_delay=0.01)
    def call_me():
        return mock_func()

    assert call_me() == "success"
    assert mock_func.call_count == 2

def test_mt5_error_retriable_attribute():
    err = MT5Error("msg", retriable=True)
    assert err.retriable is True

    err2 = MT5ExecutionError("msg", retriable=False)
    assert err2.retriable is False

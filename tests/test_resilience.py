"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_resilience.py
Resilience tests for retry logic and exception handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MT5ConnectionError, MT5DataError
from src.core.retry import with_retry


def test_retry_success_after_failure():
    """Test that @with_retry eventually succeeds."""
    mock_func = MagicMock()
    # Fail twice, then succeed
    mock_func.side_effect = [ValueError("Fail 1"), ValueError("Fail 2"), "Success"]

    @with_retry(max_retries=3, base_delay=0.01, jitter=False, exceptions=(ValueError,))
    def decorated_func():
        return mock_func()

    result = decorated_func()
    assert result == "Success"
    assert mock_func.call_count == 3

def test_retry_max_reached():
    """Test that @with_retry raises after max retries."""
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Always fail")

    @with_retry(max_retries=2, base_delay=0.01, jitter=False, exceptions=(ValueError,))
    def decorated_func():
        return mock_func()

    with pytest.raises(ValueError, match="Always fail"):
        decorated_func()

    assert mock_func.call_count == 3  # Initial call + 2 retries

def test_retry_unexpected_exception():
    """Test that @with_retry does not retry on unexpected exceptions."""
    mock_func = MagicMock()
    mock_func.side_effect = RuntimeError("Fatal")

    @with_retry(max_retries=3, base_delay=0.01, jitter=False, exceptions=(ValueError,))
    def decorated_func():
        return mock_func()

    with pytest.raises(RuntimeError, match="Fatal"):
        decorated_func()

    assert mock_func.call_count == 1

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_connection_failure(mock_mt5):
    """Test MT5Connector raises MT5ConnectionError on failure."""
    from src.core.config import TradingConfig
    from src.trading.mt5_connector import MT5Connector

    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-1, "Connection failed")

    cfg = MagicMock(spec=TradingConfig)
    cfg.mode = "live"
    cfg.mt5_path = ""
    cfg.mt5_login = 123
    cfg.mt5_password = "pw"
    cfg.mt5_server = "server"
    cfg.metaapi_token = None

    connector = MT5Connector(cfg)

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        with patch("src.trading.mt5_connector.METAAPI_AVAILABLE", False):
            with pytest.raises(MT5ConnectionError):
                # Should retry 2 times, so 3 calls total
                connector.initialize()

    assert mock_mt5.initialize.call_count == 3

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_data_failure(mock_mt5):
    """Test MT5Connector raises MT5DataError on rates failure."""
    from src.core.config import TradingConfig
    from src.trading.mt5_connector import MT5Connector

    mock_mt5.copy_rates_from_pos.return_value = None
    mock_mt5.last_error.return_value = (-2, "Data failed")

    cfg = MagicMock(spec=TradingConfig)
    connector = MT5Connector(cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), pytest.raises(MT5DataError):
        # Should retry 3 times, so 4 calls total
        connector.get_rates("XAUUSD", "M5", 100)

    assert mock_mt5.copy_rates_from_pos.call_count == 4

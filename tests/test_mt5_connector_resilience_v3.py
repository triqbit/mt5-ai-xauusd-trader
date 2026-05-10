
import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.exceptions import MT5ConnectionError, MT5DataError, CircuitBreakerError
import pandas as pd

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.mode = "demo"
    cfg.symbol = "XAUUSD"
    cfg.mt5_path = ""
    cfg.mt5_login = 12345
    cfg.mt5_password.get_secret_value.return_value = "pass"
    cfg.mt5_server = "server"
    cfg.metaapi_token = None
    return cfg

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_account_info_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)

    # 1. Test auto-initialization and success
    mock_mt5.initialize.return_value = True
    mock_acc = MagicMock()
    mock_acc._asdict.return_value = {"balance": 10000.0}
    mock_mt5.account_info.return_value = mock_acc

    info = connector.get_account_info()
    assert info["balance"] == 10000.0
    assert connector._is_initialized
    mock_mt5.initialize.assert_called_once()

    # 2. Test transient failure and retry
    mock_mt5.account_info.side_effect = [None, mock_acc]
    mock_mt5.last_error.return_value = (-1, "Terminal not connected")

    # Reset mock to check calls
    mock_mt5.initialize.reset_mock()
    # We need to patch time.sleep to speed up tests (decorator uses it)
    with patch("time.sleep"):
        info = connector.get_account_info()
        assert info["balance"] == 10000.0
        # Should have called initialize again due to _is_initialized = False on error
        assert mock_mt5.initialize.call_count == 1

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_account_balance_failure_propagation(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    # Permanent failure for account_info
    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (10001, "Connection lost")

    with patch("time.sleep"):
        with pytest.raises(MT5DataError):
            connector.get_account_balance()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_positions_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    mock_pos = MagicMock()
    mock_pos._asdict.return_value = {"ticket": 123}
    mock_mt5.positions_get.side_effect = [None, [mock_pos]]
    mock_mt5.last_error.return_value = (-1, "Transient error")

    with patch("time.sleep"):
        positions = connector.get_positions()
        assert len(positions) == 1
        assert positions[0]["ticket"] == 123

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_terminal_status_resilience(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    mock_info = MagicMock()
    mock_info._asdict.return_value = {"trade_allowed": True}
    mock_mt5.terminal_info.side_effect = [None, mock_info]
    mock_mt5.last_error.return_value = (-1, "Transient error")

    with patch("time.sleep"):
        status = connector.get_terminal_status()
        assert status["algo_trading"] is True

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_circuit_breaker_tripping(mock_mt5, mock_config):
    # Set low threshold for testing
    connector = MT5Connector(mock_config)
    connector.breaker.failure_threshold = 2
    connector._is_initialized = True

    # Prevent re-initialization from succeeding and potentially clearing circuit state
    mock_mt5.initialize.return_value = False
    mock_mt5.account_info.return_value = None
    # Use an error code that doesn't trigger re-initialization to keep control over calls
    mock_mt5.last_error.return_value = (2000, "Generic data error")

    with patch("time.sleep"):
        # The first call to get_account_info will fail and retry 3 times.
        # failure_threshold is 2, so it should trip during the retries of the FIRST public call.
        with pytest.raises(CircuitBreakerError):
            connector.get_account_info()

        assert connector.breaker.state.value == "OPEN"

        # 2nd call - should be immediately blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            connector.get_account_info()

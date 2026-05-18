
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def mock_config():
    # Don't use spec=TradingConfig as it's restrictive with MagicMock
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
def test_self_healing_get_rates(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)

    # 1. Initially initialized
    mock_mt5.initialize.return_value = True
    connector.initialize()
    assert connector._is_initialized

    # 2. Simulate connection failure on first call
    # -1 is a common MT5 error code for connection issues
    mock_mt5.copy_rates_from_pos.side_effect = [None, [{"time": 12345, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}]]
    mock_mt5.last_error.return_value = (-1, "Terminal not connected")

    # 3. Call get_rates - it should fail, reset initialized flag, retry, re-initialize, and succeed
    # We mock initialize but ensure it still sets _is_initialized
    def side_effect():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=side_effect) as mock_init:
        df = connector.get_rates("XAUUSD", "M5", 10)

        assert not df.empty
        assert connector._is_initialized
        assert mock_init.call_count == 1

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_auto_initialization_on_first_call(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    assert not connector._is_initialized

    mock_mt5.initialize.return_value = True
    mock_mt5.copy_rates_from_pos.return_value = [{"time": 12345, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}]

    df = connector.get_rates("XAUUSD", "M5", 10)
    assert connector._is_initialized
    assert not df.empty
    mock_mt5.initialize.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_get_rates_range_recovery(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True

    # Fail first, succeed second
    mock_mt5.copy_rates_range.side_effect = [None, [{"time": 12345, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05}]]
    mock_mt5.last_error.return_value = (10001, "Connection lost")
    mock_mt5.initialize.return_value = True

    def side_effect():
        connector._is_initialized = True
        return True

    with patch.object(connector, 'initialize', side_effect=side_effect) as mock_init:
        df = connector.get_rates_range("XAUUSD", "M5", datetime(2023,1,1), datetime(2023,1,2))
        assert not df.empty
        assert connector._is_initialized
        assert mock_init.call_count == 1

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_legacy_aliases(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    mock_mt5.initialize.return_value = True

    # Test disconnect -> shutdown
    with patch.object(connector, 'shutdown') as mock_shutdown:
        connector.disconnect()
        mock_shutdown.assert_called_once()

    # Test get_ohlcv -> get_rates
    with patch.object(connector, 'get_rates') as mock_get_rates:
        connector.get_ohlcv("XAUUSD", "M5", 100)
        mock_get_rates.assert_called_once_with("XAUUSD", "M5", 100)

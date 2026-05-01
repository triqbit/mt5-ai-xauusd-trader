"""
Unit tests for MT5Connector.
"""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.trading.mt5_connector import MT5Connector, TIMEFRAME_MAP
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.mt5_path = "path"
    cfg.mode = "demo"
    cfg.metaapi_token = ""
    return cfg

@pytest.fixture
def connector(mock_config):
    return MT5Connector(mock_config)

def test_connector_init(connector, mock_config):
    assert connector.cfg == mock_config
    assert connector._is_initialized is False

@patch("src.trading.mt5_connector.mt5")
def test_connector_initialize_native_success(mock_mt5, connector):
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        assert connector.initialize() is True
        assert connector._is_initialized is True
        assert connector.use_metaapi is False

@patch("src.trading.mt5_connector.mt5")
def test_connector_initialize_native_fail(mock_mt5, connector):
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = "error"
        assert connector.initialize() is False

@patch("src.trading.mt5_connector.MetaApi")
def test_connector_initialize_metaapi_success(mock_metaapi, connector, mock_config):
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", False):
        with patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            mock_config.metaapi_token = "token"
            assert connector.initialize() is True
            assert connector.use_metaapi is True
            assert connector._is_initialized is True

def test_connector_shutdown(connector):
    connector._is_initialized = True
    connector.use_metaapi = False
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        with patch("src.trading.mt5_connector.mt5") as mock_mt5:
            connector.shutdown()
            mock_mt5.shutdown.assert_called_once()
            assert connector._is_initialized is False

def test_get_rates_not_initialized(connector):
    df = connector.get_rates("XAUUSD", "M5", 10)
    assert df.empty

@patch("src.trading.mt5_connector.mt5")
def test_get_rates_native_success(mock_mt5, connector):
    connector._is_initialized = True
    connector.use_metaapi = False
    # MT5 returns a numpy array with named fields
    import numpy as np
    mock_mt5.copy_rates_from_pos.return_value = np.array(
        [(1614556800, 1.1, 1.2, 1.0, 1.15, 100, 0, 0)],
        dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'), ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4'), ('real_volume', 'i8')]
    )
    df = connector.get_rates("XAUUSD", "M5", 1)
    assert not df.empty
    assert "time" in df.columns

def test_get_tick_not_initialized(connector):
    tick = connector.get_tick("XAUUSD")
    assert tick == {"bid": 0.0, "ask": 0.0}

@patch("src.trading.mt5_connector.mt5")
def test_get_tick_native_success(mock_mt5, connector):
    connector._is_initialized = True
    connector.use_metaapi = False
    mock_tick = MagicMock()
    mock_tick.bid = 1.1
    mock_tick.ask = 1.2
    mock_mt5.symbol_info_tick.return_value = mock_tick
    tick = connector.get_tick("XAUUSD")
    assert tick == {"bid": 1.1, "ask": 1.2}

def test_get_account_balance(connector):
    connector._is_initialized = True
    connector.use_metaapi = False
    with patch.object(connector, "get_account_info") as mock_info:
        mock_info.return_value = {"balance": 1000.0}
        assert connector.get_account_balance() == 1000.0

@patch("src.trading.mt5_connector.mt5")
def test_get_positions_native(mock_mt5, connector):
    connector._is_initialized = True
    connector.use_metaapi = False
    mock_pos = MagicMock()
    mock_pos._asdict.return_value = {"ticket": 123}
    mock_mt5.positions_get.return_value = [mock_pos]
    positions = connector.get_positions("XAUUSD")
    assert len(positions) == 1
    assert positions[0]["ticket"] == 123

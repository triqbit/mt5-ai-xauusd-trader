"""Tests for src.trading.mt5_connector module."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "Server"
    cfg.mt5_path = "path/to/terminal"
    cfg.metaapi_token = "token"
    cfg.mode = "demo"
    return cfg

def test_mt5_connector_initialization(mock_config):
    connector = MT5Connector(mock_config)
    assert connector.cfg == mock_config
    assert not connector._is_initialized

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_initialize_native_success(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(mock_config)

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        success = connector.initialize()

    assert success
    assert connector._is_initialized
    assert not connector.use_metaapi
    mock_mt5.initialize.assert_called_once()

@patch("src.trading.mt5_connector.MetaApi")
@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_initialize_metaapi_fallback(mock_mt5, mock_metaapi, mock_config):
    mock_mt5.initialize.return_value = False
    connector = MT5Connector(mock_config)

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            success = connector.initialize()

    assert success
    assert connector._is_initialized
    assert connector.use_metaapi
    mock_metaapi.assert_called_once_with(mock_config.metaapi_token)

@patch("src.trading.mt5_connector.mt5")
def test_get_rates_success(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    # MT5 copy_rates returns a numpy structured array
    rates_data = np.array([
        (1618837200, 1770.0, 1775.0, 1765.0, 1772.0, 100, 0, 0)
    ], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i8'), ('real_volume', '<i8')])

    mock_mt5.copy_rates_from_pos.return_value = rates_data
    connector = MT5Connector(mock_config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        connector.initialize()
        df = connector.get_rates("XAUUSD", "M5", 1)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "time" in df.columns

def test_get_rates_not_initialized(mock_config):
    connector = MT5Connector(mock_config)
    df = connector.get_rates("XAUUSD", "M5", 1)
    assert df.empty

@patch("src.trading.mt5_connector.mt5")
def test_place_order_native_success(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1770.0, ask=1771.0)

    mock_result = MagicMock()
    mock_result.retcode = 0 # TRADE_RETCODE_DONE
    mock_result.order = 123456
    mock_mt5.order_send.return_value = mock_result
    mock_mt5.TRADE_RETCODE_DONE = 0

    connector = MT5Connector(mock_config)
    signal = MagicMock()
    signal.direction = 1
    signal.symbol = "XAUUSD"
    signal.lot_size = 0.1
    signal.stop_loss = 1760.0
    signal.take_profit = 1790.0
    signal.algorithm = "test"

    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        connector.initialize()
        ticket = connector.place_order(signal)

    assert ticket == 123456
    mock_mt5.order_send.assert_called_once()

"""Tests for MT5Connector."""
import pytest
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig
import pandas as pd
import asyncio

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.mt5_path = "/path/to/mt5"
    cfg.metaapi_token = "token"
    cfg.metaapi_account_id = "account_id"
    cfg.mode = "demo"
    return cfg

def test_mt5_connector_init(mock_config):
    connector = MT5Connector(mock_config)
    assert connector.cfg == mock_config
    assert not connector._is_initialized

@patch('src.trading.mt5_connector.mt5')
def test_initialize_native_success(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(mock_config)

    with patch('src.trading.mt5_connector.MT5_AVAILABLE', True):
        assert connector.initialize() is True
        assert connector._is_initialized
        assert not connector.use_metaapi
        mock_mt5.initialize.assert_called_once()

@patch('src.trading.mt5_connector.mt5')
def test_initialize_native_fail_fallback_disabled(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = False
    mock_config.metaapi_token = ""
    connector = MT5Connector(mock_config)

    with patch('src.trading.mt5_connector.MT5_AVAILABLE', True):
        assert connector.initialize() is False
        assert not connector._is_initialized

@patch('src.trading.mt5_connector.mt5')
def test_get_account_balance_native(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    mock_acc_info = MagicMock()
    mock_acc_info._asdict.return_value = {'balance': 10000.0}
    mock_mt5.account_info.return_value = mock_acc_info

    connector = MT5Connector(mock_config)
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', True):
        connector.initialize()
        balance = connector.get_account_balance()
        assert balance == 10000.0

@patch('src.trading.mt5_connector.MetaApi')
def test_initialize_metaapi_success(mock_metaapi_cls, mock_config):
    # Mock MT5 to fail
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', False), \
         patch('src.trading.mt5_connector.METAAPI_AVAILABLE', True):

        mock_metaapi = mock_metaapi_cls.return_value

        # Helper to create awaitable
        def as_awaitable(val):
            f = asyncio.Future()
            f.set_result(val)
            return f

        mock_account = MagicMock()
        mock_account.wait_until_connected.return_value = as_awaitable(None)
        mock_account.get_streaming_connection.return_value = MagicMock()
        mock_metaapi.metatrader_account_api.get_account.return_value = as_awaitable(mock_account)

        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi
        assert connector._is_initialized

@patch('src.trading.mt5_connector.MetaApi')
def test_metaapi_get_rates(mock_metaapi_cls, mock_config):
    with patch('src.trading.mt5_connector.MT5_AVAILABLE', False), \
         patch('src.trading.mt5_connector.METAAPI_AVAILABLE', True):

        mock_metaapi = mock_metaapi_cls.return_value

        def as_awaitable(val):
            f = asyncio.Future()
            f.set_result(val)
            return f

        mock_account = MagicMock()
        mock_account.wait_until_connected.return_value = as_awaitable(None)
        mock_account.get_streaming_connection.return_value = MagicMock()
        mock_metaapi.metatrader_account_api.get_account.return_value = as_awaitable(mock_account)

        # Mock historical candles
        mock_candles = [
            {'time': '2024-01-01T00:00:00.000Z', 'open': 2000.0, 'high': 2010.0, 'low': 1990.0, 'close': 2005.0, 'volume': 100},
            {'time': '2024-01-01T00:05:00.000Z', 'open': 2005.0, 'high': 2015.0, 'low': 2000.0, 'close': 2010.0, 'volume': 120},
        ]
        mock_account.get_historical_candles.return_value = as_awaitable(mock_candles)

        connector = MT5Connector(mock_config)
        connector.initialize()

        df = connector.get_rates("XAUUSD", "M5", 2)
        assert not df.empty
        assert len(df) == 2
        assert 'tick_volume' in df.columns
        assert df.iloc[0]['close'] == 2005.0

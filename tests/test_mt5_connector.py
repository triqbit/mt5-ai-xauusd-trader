"""Tests for src.trading.mt5_connector module."""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.mt5_login = 12345
    config.mt5_password = MagicMock()
    config.mt5_password.get_secret_value.return_value = "password"
    config.mt5_server = "server"
    config.mt5_path = "path"
    config.metaapi_token = MagicMock()
    config.metaapi_token.get_secret_value.return_value = "token"
    config.metaapi_account_id = "account_id"
    config.mode = "demo"
    return config

def test_initialize_native_success(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is False

def test_initialize_metaapi_fallback(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):

        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (1, "error")

        # Mock MetaAPI async initialization
        mock_account = MagicMock()
        mock_connection = MagicMock()
        mock_metaapi.return_value.metatrader_account_api.get_account.return_value = mock_account
        mock_account.get_streaming_connection.return_value = mock_connection

        connector = MT5Connector(mock_config)
        # Use a fake _run_async to avoid actual async loop issues in test
        connector._run_async = lambda coro: None

        assert connector.initialize() is True
        assert connector.use_metaapi is True

def test_get_rates_native(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        # Mock structured array returned by MT5
        import numpy as np
        rates = np.array(
            [(1618837200, 1780.0, 1785.0, 1775.0, 1782.0, 100, 0, 0)],
            dtype=[
                ("time", "<i8"),
                ("open", "<f8"),
                ("high", "<f8"),
                ("low", "<f8"),
                ("close", "<f8"),
                ("tick_volume", "<i8"),
                ("spread", "<i4"),
                ("real_volume", "<i8"),
            ],
        )
        mock_mt5.copy_rates_from_pos.return_value = rates
        connector = MT5Connector(mock_config)
        connector.initialize()

        df = connector.get_rates("XAUUSD", "M5", 1)
        assert not df.empty
        assert "time" in df.columns
        assert df.iloc[0]["close"] == 1782.0

def test_get_tick_metaapi(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):

        mock_mt5.initialize.return_value = False
        connector = MT5Connector(mock_config)
        connector._run_async = lambda coro: {"bid": 1800.0, "ask": 1801.0}
        connector.use_metaapi = True
        connector._is_initialized = True

        tick = connector.get_tick("XAUUSD")
        assert tick["bid"] == 1800.0
        assert tick["ask"] == 1801.0
        assert tick["spread"] == 1.0

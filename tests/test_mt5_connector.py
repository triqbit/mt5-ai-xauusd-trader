"""Tests for MT5Connector."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.trading.risk_engine import TradeSignal

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.mt5_path = "/path/to/mt5"
    cfg.metaapi_token = "token"
    cfg.metaapi_account_id = "account_id"
    cfg.mode = "demo"
    return cfg

def test_connector_initialization_native_success(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is False
        mock_mt5.initialize.assert_called_once()

def test_connector_initialization_metaapi_fallback(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.MetaApi") as mock_metaapi, \
         patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
        mock_mt5.initialize.return_value = False
        connector = MT5Connector(mock_config)
        assert connector.initialize() is True
        assert connector.use_metaapi is True
        mock_metaapi.assert_called_once_with("token")

def test_get_rates_native(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        # Mocking numpy structured array that MT5 returns
        import numpy as np
        rates = np.array([
            (1618822800, 1.1, 1.2, 1.0, 1.15, 100, 0, 0)
        ], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i8'), ('real_volume', '<i8')])

        mock_mt5.copy_rates_from_pos.return_value = rates
        connector = MT5Connector(mock_config)
        connector.initialize()
        df = connector.get_rates("EURUSD", "M5", 10)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "time" in df.columns

def test_place_order_native(mock_config):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5, \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        mock_mt5.initialize.return_value = True
        mock_mt5.symbol_info_tick.return_value.ask = 1.2000
        mock_mt5.symbol_info_tick.return_value.bid = 1.1990

        mock_result = MagicMock()
        mock_result.retcode = 10009 # TRADE_RETCODE_DONE
        mock_result.order = 123456
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009

        connector = MT5Connector(mock_config)
        connector.initialize()

        signal = TradeSignal(
            symbol="EURUSD",
            direction=1,
            entry_price=1.2000,
            stop_loss=1.1900,
            take_profit=1.2200,
            lot_size=0.1,
            algorithm="ppo",
            confidence=0.8
        )

        ticket = connector.place_order(signal)
        assert ticket == 123456

"""Tests for src.trading.mt5_connector module."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig

@pytest.fixture
def config():
    return TradingConfig(
        MT5_LOGIN=123,
        MT5_PASSWORD="pass",
        MT5_SERVER="server",
        metaapi_token="token",
        metaapi_account_id="acc_id",
        RISK_PER_TRADE=0.01
    )

@patch("src.trading.mt5_connector.mt5")
def test_initialize_native_success(mock_mt5, config):
    """Test successful native MT5 initialization."""
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        assert connector.initialize() is True
        assert connector.use_metaapi is False

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MetaApi")
def test_initialize_metaapi_fallback(mock_metaapi, mock_mt5, config):
    """Test MetaAPI fallback when native MT5 fails."""
    mock_mt5.initialize.return_value = False
    connector = MT5Connector(config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        with patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True):
            # Ensure metaapi_token is set in config
            config.metaapi_token = "valid_token"
            # Mock the async setup
            with patch.object(MT5Connector, "_run_coro", return_value=None):
                assert connector.initialize() is True
                assert connector.use_metaapi is True

@patch("src.trading.mt5_connector.mt5")
def test_get_rates_native(mock_mt5, config):
    """Test fetching rates via native SDK."""
    mock_mt5.initialize.return_value = True
    # MT5 copy_rates_from_pos returns a numpy structured array
    import numpy as np
    mock_rates = np.array([
        (1618837200, 1.1, 1.2, 1.0, 1.15, 100, 0, 0)
    ], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i8'), ('real_volume', '<i8')])

    mock_mt5.copy_rates_from_pos.return_value = mock_rates
    connector = MT5Connector(config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        connector.initialize()
        df = connector.get_rates("XAUUSD", "M5", 1)
        assert not df.empty
        assert "time" in df.columns
        assert isinstance(df["time"].iloc[0], pd.Timestamp)

@patch("src.trading.mt5_connector.mt5")
def test_get_tick_native(mock_mt5, config):
    """Test fetching latest tick via native SDK."""
    mock_mt5.initialize.return_value = True
    mock_tick = MagicMock()
    mock_tick.bid = 1800.5
    mock_tick.ask = 1800.7
    mock_mt5.symbol_info_tick.return_value = mock_tick

    connector = MT5Connector(config)
    with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
        connector.initialize()
        tick = connector.get_tick("XAUUSD")
        assert tick["bid"] == 1800.5
        assert tick["ask"] == 1800.7

"""Tests for src.trading.mt5_connector module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.core.config import TradingConfig
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def config() -> TradingConfig:
    """Fixture for TradingConfig."""
    cfg = MagicMock(spec=TradingConfig)
    cfg.mt5_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "Server"
    cfg.metaapi_token = ""
    cfg.mode = "demo"
    return cfg


def test_mt5_initialize_success(config: TradingConfig) -> None:
    """Test successful MT5 initialization."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(config)
        assert connector.initialize() is True
        assert connector._is_initialized is True


def test_mt5_initialize_fail(config: TradingConfig) -> None:
    """Test failed MT5 initialization."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = False
        connector = MT5Connector(config)
        assert connector.initialize() is False
        assert connector._is_initialized is False


def test_mt5_shutdown(config: TradingConfig) -> None:
    """Test MT5 connector shutdown."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = True
        connector = MT5Connector(config)
        connector.initialize()
        connector.shutdown()
        assert connector._is_initialized is False
        mock_mt5.shutdown.assert_called_once()


def test_get_account_balance(config: TradingConfig) -> None:
    """Test get_account_balance."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = True
        mock_acc_info = MagicMock()
        mock_acc_info._asdict.return_value = {"balance": 12345.67}
        mock_mt5.account_info.return_value = mock_acc_info
        connector = MT5Connector(config)
        connector.initialize()
        balance = connector.get_account_balance()
        assert balance == 12345.67


def test_get_tick(config: TradingConfig) -> None:
    """Test get_tick."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = True
        mock_mt5.symbol_info_tick.return_value = MagicMock(bid=1990.0, ask=2010.0)
        connector = MT5Connector(config)
        connector.initialize()
        tick = connector.get_tick("XAUUSD")
        assert tick["bid"] == 1990.0
        assert tick["ask"] == 2010.0


def test_get_rates(config: TradingConfig) -> None:
    """Test get_rates."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}), \
         patch("src.trading.mt5_connector.MT5_AVAILABLE", True), \
         patch("src.trading.mt5_connector.mt5", mock_mt5):
        mock_mt5.initialize.return_value = True
        mock_rates = np.array(
            [(1688169600, 1920.0, 1925.0, 1918.0, 1922.0, 100, 0, 0)],
            dtype=[
                ("time", "i8"),
                ("open", "f8"),
                ("high", "f8"),
                ("low", "f8"),
                ("close", "f8"),
                ("tick_volume", "i8"),
                ("spread", "i4"),
                ("real_volume", "i8"),
            ],
        )
        mock_mt5.copy_rates_from_pos.return_value = mock_rates
        connector = MT5Connector(config)
        connector.initialize()
        df = connector.get_rates("XAUUSD", "M5", 1)
        assert not df.empty
        assert df["close"].iloc[0] == 1922.0

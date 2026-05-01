import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.trading.mt5_connector import MT5Connector
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def mock_cfg():
    cfg = MagicMock(spec=TradingConfig)
    cfg.mode = "demo"
    cfg.mt5_path = "path/to/terminal"
    cfg.mt5_login = 12345
    cfg.mt5_password = "password"
    cfg.mt5_server = "server"
    cfg.metaapi_token = ""
    return cfg

def test_mt5_connector_initialization(mock_cfg):
    connector = MT5Connector(mock_cfg)
    assert connector.cfg == mock_cfg
    assert connector._is_initialized is False

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_mt5_connector_initialize_native_success(mock_mt5, mock_cfg):
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(mock_cfg)
    assert connector.initialize() is True
    assert connector._is_initialized is True
    assert connector.use_metaapi is False
    mock_mt5.initialize.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_mt5_connector_initialize_native_fail(mock_mt5, mock_cfg):
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = "Error"
    connector = MT5Connector(mock_cfg)
    assert connector.initialize() is False
    assert connector._is_initialized is False

@patch("src.trading.mt5_connector.MetaApi")
@patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True)
@patch("src.trading.mt5_connector.MT5_AVAILABLE", False)
def test_mt5_connector_initialize_metaapi_success(mock_metaapi, mock_cfg):
    mock_cfg.metaapi_token = "token"
    connector = MT5Connector(mock_cfg)
    assert connector.initialize() is True
    assert connector.use_metaapi is True
    assert connector._is_initialized is True

def test_mt5_connector_shutdown(mock_cfg):
    with patch("src.trading.mt5_connector.mt5") as mock_mt5:
        connector = MT5Connector(mock_cfg)
        connector._is_initialized = True
        connector.use_metaapi = False
        with patch("src.trading.mt5_connector.MT5_AVAILABLE", True):
            connector.shutdown()
            mock_mt5.shutdown.assert_called_once()
        assert connector._is_initialized is False

def test_mt5_connector_session_context_manager(mock_cfg):
    with patch.object(MT5Connector, "initialize", return_value=True) as mock_init, \
         patch.object(MT5Connector, "shutdown") as mock_shutdown:
        connector = MT5Connector(mock_cfg)
        with connector.session() as c:
            assert c == connector
        mock_init.assert_called_once()
        mock_shutdown.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_get_rates_success(mock_mt5, mock_cfg):
    connector = MT5Connector(mock_cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_rates = [
        {"time": 1618822800, "open": 2300.0, "high": 2305.0, "low": 2295.0, "close": 2302.0, "tick_volume": 100}
    ]
    mock_mt5.copy_rates_from_pos.return_value = mock_rates

    df = connector.get_rates("XAUUSD", "M5", 10)
    assert not df.empty
    assert "close" in df.columns
    mock_mt5.copy_rates_from_pos.assert_called_once()

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_get_tick_success(mock_mt5, mock_cfg):
    connector = MT5Connector(mock_cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_tick = MagicMock()
    mock_tick.bid = 2300.0
    mock_tick.ask = 2301.0
    mock_mt5.symbol_info_tick.return_value = mock_tick

    tick = connector.get_tick("XAUUSD")
    assert tick["bid"] == 2300.0
    assert tick["ask"] == 2301.0

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_place_order_success(mock_mt5, mock_cfg):
    connector = MT5Connector(mock_cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    signal = TradeSignal("XAUUSD", 1, 2300.0, 2290.0, 2320.0, 0.1, "test", 0.8)

    mock_tick = MagicMock()
    mock_tick.ask = 2300.0
    mock_mt5.symbol_info_tick.return_value = mock_tick

    mock_result = MagicMock()
    mock_result.retcode = 10009 # mt5.TRADE_RETCODE_DONE
    mock_result.order = 123456
    mock_mt5.order_send.return_value = mock_result
    # Manually set the constant since we patched mt5
    with patch("src.trading.mt5_connector.mt5.TRADE_RETCODE_DONE", 10009):
        ticket = connector.place_order(signal)
        assert ticket == 123456

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_get_account_info(mock_mt5, mock_cfg):
    connector = MT5Connector(mock_cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_acc = MagicMock()
    mock_acc._asdict.return_value = {"balance": 10000.0}
    mock_mt5.account_info.return_value = mock_acc

    info = connector.get_account_info()
    assert info["balance"] == 10000.0

@patch("src.trading.mt5_connector.mt5")
def test_mt5_connector_get_positions(mock_mt5, mock_cfg):
    connector = MT5Connector(mock_cfg)
    connector._is_initialized = True
    connector.use_metaapi = False

    mock_p = MagicMock()
    mock_p._asdict.return_value = {"ticket": 1}
    mock_mt5.positions_get.return_value = [mock_p]

    pos = connector.get_positions("XAUUSD")
    assert len(pos) == 1
    assert pos[0]["ticket"] == 1

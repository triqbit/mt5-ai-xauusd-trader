from unittest.mock import MagicMock, patch

import pytest

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.trading.mt5_connector import MT5Connector


@pytest.fixture
def mock_config():
    return TradingConfig(MT5_PASSWORD="test", MT5_SERVER="test")

def test_connector_init(mock_config):
    connector = MT5Connector(mock_config)
    assert connector.cfg == mock_config
    assert not connector._is_initialized

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_native_initialization(mock_mt5, mock_config):
    mock_mt5.initialize.return_value = True
    connector = MT5Connector(mock_config)
    assert connector.initialize()
    assert connector._is_initialized
    assert not connector.use_metaapi

@patch("src.trading.mt5_connector.MetaApi")
@patch("src.trading.mt5_connector.METAAPI_AVAILABLE", True)
@patch("src.trading.mt5_connector.MT5_AVAILABLE", False)
def test_metaapi_fallback(mock_metaapi, mock_config):
    mock_config.metaapi_token = MagicMock()
    mock_config.metaapi_token.get_secret_value.return_value = "token"
    mock_config.metaapi_account_id = "acc_id"

    # Mocking the async parts
    mock_metaapi_instance = mock_metaapi.return_value
    mock_metaapi_instance.metatrader_account_api.get_account = MagicMock()

    with patch("asyncio.run"):
        connector = MT5Connector(mock_config)
        assert connector.initialize()
        assert connector.use_metaapi
        assert connector._is_initialized

@patch("src.trading.mt5_connector.mt5")
@patch("src.trading.mt5_connector.MT5_AVAILABLE", True)
def test_place_order_native(mock_mt5, mock_config):
    connector = MT5Connector(mock_config)
    connector._is_initialized = True
    connector.use_metaapi = False

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.8
    )

    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=2300.0, bid=2299.0)
    mock_mt5.order_send.return_value = MagicMock(retcode=0, order=12345)
    mock_mt5.TRADE_RETCODE_DONE = 0

    ticket = connector.place_order(signal)
    assert ticket == 12345
    mock_mt5.order_send.assert_called_once()

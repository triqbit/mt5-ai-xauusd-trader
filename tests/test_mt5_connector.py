"""
Unit tests for src/trading/mt5_connector.py
Step 5: Test Coverage (PHASE1_ROADMAP)
All MT5 SDK calls are fully mocked -- no MetaTrader5 installation required.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Provide a stub MetaTrader5 module so the import succeeds in CI
# ---------------------------------------------------------------------------

def _make_mt5_stub() -> ModuleType:
    stub = ModuleType("MetaTrader5")
    stub.initialize = MagicMock(return_value=True)  # type: ignore[attr-defined]
    stub.shutdown = MagicMock()  # type: ignore[attr-defined]
    stub.login = MagicMock(return_value=True)  # type: ignore[attr-defined]
    stub.account_info = MagicMock()  # type: ignore[attr-defined]
    stub.symbol_info_tick = MagicMock()  # type: ignore[attr-defined]
    stub.copy_rates_from_pos = MagicMock(return_value=None)  # type: ignore[attr-defined]
    stub.order_send = MagicMock()  # type: ignore[attr-defined]
    stub.last_error = MagicMock(return_value=(0, "OK"))  # type: ignore[attr-defined]
    stub.positions_get = MagicMock(return_value=[])  # type: ignore[attr-defined]
    stub.TRADE_ACTION_DEAL = 1  # type: ignore[attr-defined]
    stub.ORDER_TYPE_BUY = 0  # type: ignore[attr-defined]
    stub.ORDER_TYPE_SELL = 1  # type: ignore[attr-defined]
    stub.ORDER_FILLING_IOC = 2  # type: ignore[attr-defined]
    stub.TRADE_RETCODE_DONE = 10009  # type: ignore[attr-defined]
    return stub


# Inject stub before importing the connector
if "MetaTrader5" not in sys.modules:
    sys.modules["MetaTrader5"] = _make_mt5_stub()

from src.trading.mt5_connector import MT5Connector  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> MagicMock:
    cfg = MagicMock()
    cfg.mt5_login = 12345
    cfg.mt5_password = "secret"
    cfg.mt5_server = "BrokerServer"
    cfg.mt5_path = None
    cfg.use_metaapi = False
    cfg.metaapi_token = ""
    cfg.metaapi_account_id = ""
    cfg.mode = "demo"
    return cfg


@pytest.fixture
def connector(config: MagicMock) -> MT5Connector:
    return MT5Connector(config=config)


@pytest.fixture
def connected_connector(connector: MT5Connector) -> MT5Connector:
    """Connector with _is_initialized set to True for testing."""
    connector._is_initialized = True
    connector.use_metaapi = False
    return connector


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestMT5ConnectorInit:
    def test_connector_created(self, connector: MT5Connector) -> None:
        assert connector is not None

    def test_config_stored(self, connector: MT5Connector, config: MagicMock) -> None:
        assert connector.cfg is config

    def test_not_initialized_by_default(self, connector: MT5Connector) -> None:
        assert connector._is_initialized is False

    def test_use_metaapi_false_by_default(self, connector: MT5Connector) -> None:
        assert connector.use_metaapi is False


# ---------------------------------------------------------------------------
# connect() / disconnect()
# ---------------------------------------------------------------------------

class TestConnectDisconnect:
    def test_connect_calls_initialize(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mt5.initialize.return_value = True  # type: ignore[attr-defined]
        result = connector.connect()
        mt5.initialize.assert_called()  # type: ignore[attr-defined]

    def test_disconnect_calls_shutdown(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        connected_connector.disconnect()
        mt5.shutdown.assert_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# get_account_info()
# ---------------------------------------------------------------------------

class TestAccountInfo:
    def test_returns_empty_dict_when_not_initialized(self, connector: MT5Connector) -> None:
        result = connector.get_account_info()
        assert result == {}

    def test_returns_account_info_when_initialized(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mock_info = MagicMock()
        mock_info._asdict.return_value = {"balance": 10000.0, "equity": 10000.0}  # type: ignore[attr-defined]
        mt5.account_info.return_value = mock_info  # type: ignore[attr-defined]
        result = connected_connector.get_account_info()
        assert result is not None
        assert result["balance"] == 10000.0


# ---------------------------------------------------------------------------
# get_tick()
# ---------------------------------------------------------------------------

class TestGetTick:
    def test_returns_zero_bid_ask_when_not_initialized(self, connector: MT5Connector) -> None:
        result = connector.get_tick("XAUUSD")
        assert result["bid"] == 0.0
        assert result["ask"] == 0.0

    def test_returns_tick_dict_when_initialized(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mock_tick = MagicMock()
        mock_tick.bid = 1900.0
        mock_tick.ask = 1900.5
        mt5.symbol_info_tick.return_value = mock_tick  # type: ignore[attr-defined]
        result = connected_connector.get_tick("XAUUSD")
        assert result["bid"] == 1900.0
        assert result["ask"] == 1900.5

    def test_returns_zero_on_failed_tick(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mt5.symbol_info_tick.return_value = None  # type: ignore[attr-defined]
        result = connected_connector.get_tick("XAUUSD")
        assert result["bid"] == 0.0
        assert result["ask"] == 0.0


# ---------------------------------------------------------------------------
# place_order()
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    def test_returns_none_when_not_initialized(self, connector: MT5Connector) -> None:
        signal = MagicMock()
        signal.symbol = "XAUUSD"
        signal.direction = 1
        signal.lot_size = 0.01
        signal.stop_loss = 1890.0
        signal.take_profit = 1910.0
        signal.algorithm = "test"
        result = connector.place_order(signal)
        assert result is None

    def test_places_buy_order(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mock_tick = MagicMock()
        mock_tick.bid = 1900.0
        mock_tick.ask = 1900.5
        mt5.symbol_info_tick.return_value = mock_tick  # type: ignore[attr-defined]
        mock_result = MagicMock()
        mock_result.retcode = mt5.TRADE_RETCODE_DONE
        mock_result.order = 12345
        mt5.order_send.return_value = mock_result  # type: ignore[attr-defined]
        signal = MagicMock()
        signal.symbol = "XAUUSD"
        signal.direction = 1  # BUY
        signal.lot_size = 0.01
        signal.stop_loss = 1890.0
        signal.take_profit = 1910.0
        signal.algorithm = "test"
        result = connected_connector.place_order(signal)
        assert result == 12345
        mt5.order_send.assert_called_once()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# get_account_balance()
# ---------------------------------------------------------------------------

class TestGetAccountBalance:
    def test_returns_zero_when_not_initialized(self, connector: MT5Connector) -> None:
        result = connector.get_account_balance()
        assert result == 0.0

    def test_returns_balance_when_initialized(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mock_info = MagicMock()
        mock_info._asdict.return_value = {"balance": 5000.0}  # type: ignore[attr-defined]
        mt5.account_info.return_value = mock_info  # type: ignore[attr-defined]
        result = connected_connector.get_account_balance()
        assert result == 5000.0


# ---------------------------------------------------------------------------
# get_positions()
# ---------------------------------------------------------------------------

class TestGetPositions:
    def test_returns_empty_list_when_not_initialized(self, connector: MT5Connector) -> None:
        result = connector.get_positions()
        assert result == []

    def test_returns_positions_list(self, connected_connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mock_pos = MagicMock()
        mock_pos._asdict.return_value = {"symbol": "XAUUSD", "volume": 0.1}  # type: ignore[attr-defined]
        mt5.positions_get.return_value = [mock_pos]  # type: ignore[attr-defined]
        result = connected_connector.get_positions()
        assert len(result) == 1
        assert result[0]["symbol"] == "XAUUSD"

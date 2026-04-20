"""
Unit tests for src/trading/mt5_connector.py
Step 5: Test Coverage (PHASE1_ROADMAP)
All MT5 SDK calls are fully mocked -- no MetaTrader5 installation required.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

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
    stub.TRADE_ACTION_DEAL = 1  # type: ignore[attr-defined]
    stub.ORDER_TYPE_BUY = 0  # type: ignore[attr-defined]
    stub.ORDER_TYPE_SELL = 1  # type: ignore[attr-defined]
    stub.ORDER_FILLING_IOC = 2  # type: ignore[attr-defined]
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
    cfg.use_metaapi = False
    cfg.metaapi_token = ""
    cfg.metaapi_account_id = ""
    return cfg


@pytest.fixture
def connector(config: MagicMock) -> MT5Connector:
    return MT5Connector(config=config)


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestMT5ConnectorInit:
    def test_connector_created(self, connector: MT5Connector) -> None:
        assert connector is not None

    def test_config_stored(self, connector: MT5Connector, config: MagicMock) -> None:
        assert connector.cfg is config

    def test_not_connected_by_default(self, connector: MT5Connector) -> None:
        assert connector.connected is False


# ---------------------------------------------------------------------------
# connect() / disconnect()
# ---------------------------------------------------------------------------

class TestConnectDisconnect:
    def test_connect_calls_initialize(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        mt5.initialize.return_value = True  # type: ignore[attr-defined]
        mt5.login.return_value = True  # type: ignore[attr-defined]
        connector.connect()
        mt5.initialize.assert_called()  # type: ignore[attr-defined]

    def test_disconnect_calls_shutdown(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        connector.connected = True
        connector.disconnect()
        mt5.shutdown.assert_called()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# get_account_info()
# ---------------------------------------------------------------------------

class TestAccountInfo:
    def test_returns_none_when_not_connected(self, connector: MT5Connector) -> None:
        connector.connected = False
        result = connector.get_account_info()
        assert result is None
    def test_returns_account_info_when_connected(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        connector.connected = True
        mock_info = MagicMock()
        mock_info._asdict.return_value = {"balance": 10000.0, "equity": 10000.0}  # type: ignore[attr-defined]
        mt5.account_info.return_value = mock_info  # type: ignore[attr-defined]
        result = connector.get_account_info()
        assert result is not None
        assert result["balance"] == 10000.0


# ---------------------------------------------------------------------------
# get_symbol_tick()
# ---------------------------------------------------------------------------

class TestGetSymbolTick:
    def test_returns_none_when_not_connected(self, connector: MT5Connector) -> None:
        connector.connected = False
        result = connector.get_symbol_tick("XAUUSD")
        assert result is None

    def test_returns_tick_dict_when_connected(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        connector.connected = True
        mock_tick = MagicMock()
        mock_tick._asdict.return_value = {"bid": 1900.0, "ask": 1900.5}  # type: ignore[attr-defined]
        mt5.symbol_info_tick.return_value = mock_tick  # type: ignore[attr-defined]
        result = connector.get_symbol_tick("XAUUSD")
        assert result is not None
        assert result["bid"] == 1900.0


# ---------------------------------------------------------------------------
# place_order()
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    def test_returns_none_when_not_connected(self, connector: MT5Connector) -> None:
        connector.connected = False
        result = connector.place_order(
            symbol="XAUUSD",
            order_type="buy",
            volume=0.01,
            price=1900.0,
        )
        assert result is None

    def test_places_buy_order(self, connector: MT5Connector) -> None:
        mt5 = sys.modules["MetaTrader5"]
        connector.connected = True
        mock_result = MagicMock()
        mock_result.retcode = 10009  # TRADE_RETCODE_DONE
        mock_result._asdict.return_value = {"retcode": 10009, "order": 12345}  # type: ignore[attr-defined]
        mt5.order_send.return_value = mock_result  # type: ignore[attr-defined]
        result = connector.place_order(
            symbol="XAUUSD",
            order_type="buy",
            volume=0.01,
            price=1900.0,
        )
        assert result is not None
        mt5.order_send.assert_called_once()  # type: ignore[attr-defined]

"""Tests for src.trading.order_manager module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading.mt5_connector import MT5Connector
from src.trading.order_manager import OrderManager


@pytest.fixture
def connector() -> MagicMock:
    """Fixture for MT5Connector mock."""
    conn = MagicMock(spec=MT5Connector)
    conn.use_metaapi = False
    conn.get_tick = AsyncMock(return_value={"bid": 1999.0, "ask": 2001.0})
    return conn


@pytest.fixture
def order_manager(connector: MagicMock) -> OrderManager:
    """Fixture for OrderManager."""
    return OrderManager(connector, symbol="XAUUSD")


@pytest.mark.asyncio
async def test_execute_trade_buy_mt5(order_manager: OrderManager, connector: MagicMock) -> None:
    """Test BUY trade execution via MT5 desktop."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}):
        mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=123456, deal=789012)
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 1
        mock_mt5.ORDER_FILLING_IOC = 1

        result = await order_manager.execute_trade("BUY", 0.1, sl_pips=50, tp_pips=100)

        assert result["status"] == "success"
        assert result["order_id"] == 123456


@pytest.mark.asyncio
async def test_execute_trade_sell_mt5(order_manager: OrderManager, connector: MagicMock) -> None:
    """Test SELL trade execution via MT5 desktop."""
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}):
        mock_mt5.order_send.return_value = MagicMock(retcode=10009, order=654321)
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1

        result = await order_manager.execute_trade("SELL", 0.1)

        assert result["status"] == "success"
        assert result["order_id"] == 654321


def test_calculate_sl_tp(order_manager: OrderManager) -> None:
    """Test SL/TP calculation."""
    # BUY: price 2000, sl_pips 50 (0.1/pip) -> 2000 - 5 = 1995
    sl, tp = order_manager._calculate_sl_tp("BUY", 2000.0, 50.0, 100.0)
    assert sl == 1995.0
    assert tp == 2010.0

    # SELL: price 2000, sl_pips 50 -> 2000 + 5 = 2005
    sl, tp = order_manager._calculate_sl_tp("SELL", 2000.0, 50.0, 100.0)
    assert sl == 2005.0
    assert tp == 1990.0

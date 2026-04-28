"""Tests for src.trading.portfolio_manager module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading.mt5_connector import MT5Connector
from src.trading.portfolio_manager import PortfolioManager


@pytest.fixture
def connector() -> MagicMock:
    """Fixture for MT5Connector mock."""
    conn = MagicMock(spec=MT5Connector)
    conn.use_metaapi = False
    conn.get_account_balance = AsyncMock(return_value={
        "balance": 10000.0,
        "equity": 10500.0,
        "profit": 500.0,
        "margin": 1000.0,
        "margin_free": 9000.0
    })
    conn.get_positions = MagicMock(return_value=[
        {"ticket": 1, "symbol": "XAUUSD", "volume": 0.1, "profit": 200.0},
        {"ticket": 2, "symbol": "XAUUSD", "volume": 0.2, "profit": 300.0}
    ])
    return conn


@pytest.fixture
def portfolio_manager(connector: MagicMock) -> PortfolioManager:
    """Fixture for PortfolioManager."""
    return PortfolioManager(connector)


@pytest.mark.asyncio
async def test_get_account_summary(portfolio_manager: PortfolioManager) -> None:
    """Test account summary retrieval."""
    summary = await portfolio_manager.get_account_summary()
    assert summary["balance"] == 10000.0
    assert summary["equity"] == 10500.0
    assert summary["profit"] == 500.0


@pytest.mark.asyncio
async def test_get_symbol_exposure(portfolio_manager: PortfolioManager, connector: MagicMock) -> None:
    """Test symbol exposure calculation."""
    # Mocking MetaTrader5 because it's used in get_symbol_exposure
    mock_mt5 = MagicMock()
    with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}):
        mock_mt5.positions_get.return_value = [
            MagicMock(volume=0.1, type=0),  # BUY
            MagicMock(volume=0.2, type=0)   # BUY
        ]
        mock_mt5.POSITION_TYPE_BUY = 0

        exposure = await portfolio_manager.get_symbol_exposure("XAUUSD")
        assert exposure == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_check_drawdown(portfolio_manager: PortfolioManager) -> None:
    """Test drawdown calculation."""
    drawdown = await portfolio_manager.check_drawdown(10000.0)
    # equity is 10500, so drawdown should be 0 (profit)
    assert drawdown == 0.0

    portfolio_manager.connector.get_account_balance.return_value = {"equity": 9000.0}
    drawdown = await portfolio_manager.check_drawdown(10000.0)
    assert drawdown == 10.0


@pytest.mark.asyncio
async def test_get_account_summary_exception(portfolio_manager: PortfolioManager) -> None:
    """Test account summary retrieval with exception."""
    portfolio_manager.connector.get_account_balance.side_effect = Exception("Test error")
    summary = await portfolio_manager.get_account_summary()
    assert summary == {}


@pytest.mark.asyncio
async def test_get_symbol_exposure_exception(portfolio_manager: PortfolioManager) -> None:
    """Test symbol exposure calculation with exception."""
    # This will trigger Exception in try-except because MetaTrader5 is not in sys.modules yet
    # or because we force an error
    with patch.dict("sys.modules", {"MetaTrader5": None}):
        exposure = await portfolio_manager.get_symbol_exposure("XAUUSD")
        assert exposure == 0.0

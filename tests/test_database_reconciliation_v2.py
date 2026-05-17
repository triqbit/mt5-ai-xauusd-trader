"""
Tests for RiskManager and TradeLogger state reconciliation.
"""

import pytest
from datetime import datetime, UTC, timedelta
from src.core.trade_logger import TradeLogger, Trade
from src.trading.risk_manager import RiskManager
from src.core.config import get_config

import uuid

@pytest.fixture
def db_url():
    return f"sqlite:///:memory-recon-test-{uuid.uuid4()}:"

@pytest.fixture
def trade_logger(db_url):
    logger = TradeLogger(db_url=db_url)
    return logger

@pytest.fixture
def risk_manager(trade_logger):
    from src.core.config import TradingConfig
    cfg = TradingConfig(
        MT5_LOGIN=123456,
        MT5_PASSWORD="password",
        MT5_SERVER="server",
        SYMBOL="XAUUSD"
    )
    return RiskManager(config=cfg, account_balance=10000.0, logger_db=trade_logger)

def test_trade_logger_reconciliation_data(trade_logger):
    # Setup: Log some closed trades
    # One from yesterday, two from today
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)

    with trade_logger.Session() as session:
        # Trade from yesterday
        t1 = Trade(
            ticket=100, symbol="XAUUSD", direction=1, entry_price=2000.0,
            exit_price=2010.0, lot_size=0.1, pnl=100.0, status="CLOSED"
        )
        t1.created_at = yesterday
        t1.updated_at = yesterday

        # Trade from today (win)
        t2 = Trade(
            ticket=101, symbol="XAUUSD", direction=1, entry_price=2010.0,
            exit_price=2020.0, lot_size=0.1, pnl=100.0, status="CLOSED"
        )

        # Trade from today (loss)
        t3 = Trade(
            ticket=102, symbol="XAUUSD", direction=-1, entry_price=2020.0,
            exit_price=2025.0, lot_size=0.1, pnl=-50.0, status="CLOSED"
        )

        # Open trade
        t4 = Trade(
            ticket=103, symbol="XAUUSD", direction=1, entry_price=2025.0,
            lot_size=0.1, status="OPEN"
        )

        session.add_all([t1, t2, t3, t4])
        session.commit()

    recon_data = trade_logger.get_reconciliation_data()

    assert recon_data["daily_pnl"] == 50.0  # 100 - 50
    assert recon_data["daily_count"] == 2
    assert len(recon_data["pnl_series"]) == 3
    assert recon_data["pnl_series"] == [100.0, 100.0, -50.0]

    open_trades = trade_logger.get_open_trades()
    assert open_trades == {"XAUUSD": 103}

def test_risk_manager_state_reconciliation(risk_manager, trade_logger):
    # Mock reconciliation data
    recon_data = {
        "daily_pnl": 150.0,
        "daily_count": 3,
        "pnl_series": [100.0, -50.0, 200.0, -100.0] # Peak at 100-50+200 = 250
    }

    risk_manager.reconcile_state(initial_balance=10000.0, reconciled_data=recon_data)

    assert risk_manager.daily.realised_pnl == 150.0
    assert risk_manager.daily.trade_count == 3
    assert risk_manager.peak_equity == 10250.0 # 10000 + 250

def test_risk_manager_reconciliation_only_losses(risk_manager):
    # Handles accounts with only losses correctly
    recon_data = {
        "daily_pnl": -200.0,
        "daily_count": 2,
        "pnl_series": [-100.0, -100.0]
    }

    risk_manager.reconcile_state(initial_balance=10000.0, reconciled_data=recon_data)

    assert risk_manager.peak_equity == 10000.0 # Should not drop below initial balance
    assert risk_manager.daily.realised_pnl == -200.0

def test_risk_manager_reconciliation_empty(risk_manager):
    recon_data = {
        "daily_pnl": 0.0,
        "daily_count": 0,
        "pnl_series": []
    }

    risk_manager.reconcile_state(initial_balance=10000.0, reconciled_data=recon_data)

    assert risk_manager.peak_equity == 10000.0
    assert risk_manager.daily.realised_pnl == 0.0
    assert risk_manager.daily.trade_count == 0

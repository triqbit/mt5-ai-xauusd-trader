
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.core.trade_logger import Trade, TradeLogger
from src.trading.risk_manager import RiskManager


class MockConfig:
    def __init__(self):
        self.risk_per_trade = 0.01
        self.max_daily_loss = 0.05
        self.max_positions = 3
        self.max_losing_streak = 5
        self.model_drift_threshold = 0.1
        self.model_accuracy_floor = 0.5
        self.model_calibration_threshold = 0.2

@pytest.fixture
def db_url():
    # Use a unique in-memory database for each test to avoid engine caching side effects
    return f"sqlite:///:memory-{uuid.uuid4()}:"

@pytest.fixture
def trade_logger(db_url):
    return TradeLogger(db_url)

@pytest.fixture
def risk_manager(trade_logger):
    cfg = MockConfig()
    return RiskManager(config=cfg, account_balance=10000.0, logger_db=trade_logger)

def test_risk_reconciliation_cycle(trade_logger, risk_manager):
    # 1. Setup historical data in DB
    # We'll simulate a sequence where we had 2 trades yesterday and 2 trades today.
    # Total PnL: 100 + 200 + 200 - 50 = 450
    # Today's PnL: 200 - 50 = 150
    # Historical Max PnL: 500 (after first 3 trades)

    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)

    with trade_logger.Session() as session:
        # Yesterday's trades
        t1 = Trade(ticket=1001, symbol="XAUUSD", direction=1, entry_price=2000.0, exit_price=2001.0, lot_size=1.0, pnl=100.0, status="CLOSED")
        t1.created_at = yesterday
        t1.updated_at = yesterday

        t2 = Trade(ticket=1002, symbol="XAUUSD", direction=1, entry_price=2000.0, exit_price=2002.0, lot_size=1.0, pnl=200.0, status="CLOSED")
        t2.created_at = yesterday
        t2.updated_at = yesterday

        # Today's trades
        t3 = Trade(ticket=1003, symbol="XAUUSD", direction=1, entry_price=2000.0, exit_price=2002.0, lot_size=1.0, pnl=200.0, status="CLOSED")
        t3.created_at = now
        t3.updated_at = now

        t4 = Trade(ticket=1004, symbol="XAUUSD", direction=-1, entry_price=2000.0, exit_price=2000.5, lot_size=1.0, pnl=-50.0, status="CLOSED")
        t4.created_at = now
        t4.updated_at = now

        # Open trade
        t5 = Trade(ticket=1005, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=1.0, status="OPEN")

        session.add_all([t1, t2, t3, t4, t5])
        session.commit()

    # 2. Run reconciliation
    # Current balance is assumed to be 10450.0 (10000 base + 450 total pnl)
    current_balance = 10450.0
    risk_manager.reconcile_state(current_balance)

    # 3. Verify state
    assert risk_manager.daily.realised_pnl == 150.0
    assert risk_manager.daily.trade_count == 2
    assert "XAUUSD" in risk_manager.open_positions
    assert risk_manager.open_positions["XAUUSD"] == 1005

    # Total PnL = 450.0
    # Peak PnL was 500.0 (after t1, t2, t3)
    # Deposit = 10450 - 450 = 10000
    # Peak Equity = 10000 + 500 = 10500
    assert risk_manager.peak_equity == 10500.0
    assert risk_manager.daily.peak_equity == 10500.0

def test_reconciliation_empty_db(trade_logger, risk_manager):
    risk_manager.reconcile_state(10000.0)
    assert risk_manager.daily.realised_pnl == 0.0
    assert risk_manager.daily.trade_count == 0
    assert len(risk_manager.open_positions) == 0
    assert risk_manager.peak_equity == 10000.0

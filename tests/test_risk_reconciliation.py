"""
End-to-end test for RiskManager state reconciliation.
"""

import os
from datetime import UTC, datetime, timedelta

import pytest
from src.core.trade_logger import TradeLogger, Trade, Base
from src.trading.risk_manager import RiskManager
from src.core.config import TradingConfig

@pytest.fixture
def logger():
    db_path = "test_recon.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    Base.metadata.create_all(logger.engine)
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def config():
    return TradingConfig(
        SYMBOL="XAUUSD",
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=5,
        max_losing_streak=3,
        MT5_LOGIN=12345,
        MT5_PASSWORD="password",
        MT5_SERVER="demo"
    )

def test_risk_reconciliation_flow(logger, config):
    # 1. Simulate some closed trades from earlier today
    now = datetime.now(UTC)

    # Trade 1: Win
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0) # Realised +100

    # Trade 2: Loss
    logger.log_trade(2, "XAUUSD", -1, 2005.0, 0.1, status="OPEN")
    logger.update_trade(2, 2010.0, -50.0) # Realised -50

    # Trade 3: Open position
    logger.log_trade(3, "XAUUSD", 1, 2008.0, 0.1, status="OPEN")

    # 2. Fetch reconciliation data
    recon_data = logger.get_reconciliation_data()
    open_trades = logger.get_open_trades()

    assert recon_data["today_realised_pnl"] == 50.0
    assert recon_data["today_trade_count"] == 2
    assert recon_data["today_consecutive_losses"] == 1
    assert recon_data["total_pnl"] == 50.0
    assert len(open_trades) == 1
    assert open_trades[0].ticket == 3

    # 3. Initialize new RiskManager (simulating restart)
    balance = 10050.0 # Starting 10000 + 50 profit
    risk = RiskManager(config, account_balance=balance, logger_db=logger)

    # Initial state (incorrect after restart without recon)
    assert risk.daily.realised_pnl == 0.0
    assert risk.peak_equity == 10050.0

    # 4. Reconcile
    risk.reconcile_state(recon_data)
    for trade in open_trades:
        risk.open_positions[trade.symbol] = trade.ticket

    # Verified state
    assert risk.daily.realised_pnl == 50.0
    assert risk.daily.trade_count == 2
    assert risk.daily.consecutive_losses == 1
    assert risk.open_positions["XAUUSD"] == 3

    # All-time peak should be 10100 (initial 10000 + 100 profit from trade 1)
    # total_pnl is 50. initial_balance = 10050 - 50 = 10000.
    # peak_pnl is 100. initial_balance + peak_pnl = 10100.
    assert risk.peak_equity == 10100.0

def test_daily_peak_equity_reconciliation(logger, config):
    # Scenario: profit then loss. Daily peak equity should be the highest point.
    logger.log_trade(10, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(10, 2020.0, 200.0)

    logger.log_trade(11, "XAUUSD", 1, 2020.0, 0.1, status="OPEN")
    logger.update_trade(11, 2010.0, -100.0)

    recon_data = logger.get_reconciliation_data()

    # current balance = 10000 + 200 - 100 = 10100
    risk = RiskManager(config, account_balance=10100.0, logger_db=logger)
    risk.reconcile_state(recon_data)

    # today_peak_pnl = 200.
    # today_start_balance = 10100 - 100 (net today) = 10000.
    # daily.peak_equity = 10000 + 200 = 10200.
    assert risk.daily.peak_equity == 10200.0
    assert risk.peak_equity == 10200.0

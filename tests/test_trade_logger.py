"""
Integration tests for TradeLogger - Enterprise Edition.
"""
import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from src.core.trade_logger import TradeLogger, Trade, ModelSignal, RiskEvent, PerformanceMetric

@pytest.fixture
def logger():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    # Ensure we start fresh
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_log_signal_audit(logger):
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ppo",
        "confidence": 0.8,
        "created_by": "test_user"
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

    with logger.Session() as session:
        signal = session.get(ModelSignal, signal_id)
        assert signal.symbol == "XAUUSD"
        assert signal.created_by == "test_user"
        assert signal.created_at is not None

def test_log_trade_constraints(logger):
    # Testing valid trade
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        created_by="executor"
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.get(Trade, trade_id)
        assert trade.ticket == 12345
        assert trade.created_by == "executor"

def test_performance_report_calculation(logger):
    # Log and close trades to test Profit Factor and Sharpe
    # Trade 1: Profit 100
    t1 = logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1)
    logger.update_trade(1, 2010.0, 100.0) # pnl=100

    # Trade 2: Loss 50
    t2 = logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1)
    logger.update_trade(2, 2005.0, -50.0) # pnl=-50

    report = logger.read_performance_report()

    # PF = 100 / 50 = 2.0
    assert report["profit_factor"] == 2.0
    # Sharpe should be non-zero as we have variance
    assert report["sharpe_ratio"] != 0
    # Max DD: Peak was 100, then dropped to 50. DD = 50.
    assert report["max_drawdown"] == 50.0

    # Verify persistence
    with logger.Session() as session:
        metric = session.query(PerformanceMetric).order_by(PerformanceMetric.id.desc()).first()
        assert metric.profit_factor == 2.0
        assert metric.max_drawdown == 50.0

def test_log_risk_event_audit(logger):
    logger.log_risk_event(
        event_type="CIRCUIT_BREAKER",
        description="Daily loss limit exceeded",
        symbol="XAUUSD",
        created_by="risk_engine"
    )

    with logger.Session() as session:
        stmt = select(RiskEvent).where(RiskEvent.event_type == "CIRCUIT_BREAKER")
        event = session.execute(stmt).scalar_one()
        assert event.symbol == "XAUUSD"
        assert event.created_by == "risk_engine"

def test_update_trade_audit(logger):
    logger.log_trade(101, "XAUUSD", 1, 2300.0, 0.01)
    logger.update_trade(101, 2310.0, pnl=10.0, updated_by="closer")

    with logger.Session() as session:
        trade = session.execute(select(Trade).where(Trade.ticket == 101)).scalar_one()
        assert trade.status == "CLOSED"
        assert trade.updated_by == "closer"
        assert trade.pnl == 10.0

"""
Integration tests for TradeLogger.
"""
import os
import pytest
from datetime import datetime, timezone
from src.core.trade_logger import TradeLogger, ModelSignal, Trade, RiskEvent, PerformanceMetric

@pytest.fixture
def logger():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    # Ensure fresh DB for each test
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_log_signal(logger):
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "algorithm": "ppo",
        "confidence": 0.8
    }
    user = "test_user"
    signal_id = logger.log_signal(signal_data, user=user)
    assert signal_id > 0

    with logger.Session() as session:
        signal = session.get(ModelSignal, signal_id)
        assert signal.symbol == "XAUUSD"
        assert signal.created_by == user
        assert signal.updated_by == user
        assert signal.created_at is not None

def test_log_trade(logger):
    user = "trader_1"
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    }, user=user)

    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        user=user
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.get(Trade, trade_id)
        assert trade.ticket == 12345
        assert trade.created_by == user
        assert trade.signal_id == signal_id

def test_update_trade(logger):
    user = "updater"
    logger.log_trade(
        ticket=111,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        user="system"
    )

    logger.update_trade(111, exit_price=2010.0, pnl=100.0, user=user)

    with logger.Session() as session:
        from sqlalchemy import select
        stmt = select(Trade).where(Trade.ticket == 111)
        trade = session.execute(stmt).scalar_one()
        assert trade.status == "CLOSED"
        assert trade.pnl == 100.0
        assert trade.updated_by == user

def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0)

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, -50.0)

    report = logger.read_performance_report(user="analyzer")
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    # Max drawdown calculation: equity curve [100, 50], peak 100, DD at 50 is 50.
    assert report["max_drawdown"] == 50.0

    with logger.Session() as session:
        from sqlalchemy import select
        stmt = select(PerformanceMetric).order_by(PerformanceMetric.id.desc())
        metric = session.execute(stmt).scalars().first()
        assert metric.profit_factor == 2.0
        assert metric.created_by == "analyzer"

def test_log_risk_event(logger):
    user = "risk_mgr"
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit", user=user)

    with logger.Session() as session:
        from sqlalchemy import select
        stmt = select(RiskEvent).where(RiskEvent.event_type == "CIRCUIT_BREAKER")
        event = session.execute(stmt).scalars().first()
        assert event.description == "Drawdown limit hit"
        assert event.created_by == user

def test_soft_delete(logger):
    trade_id = logger.log_trade(ticket=999, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.1)

    with logger.Session() as session:
        trade = session.get(Trade, trade_id)
        trade.is_deleted = True
        trade.deleted_at = datetime.now(timezone.utc)
        session.commit()

    # Should not be included in performance report
    report = logger.read_performance_report()
    assert report["sharpe_ratio"] == 0.0 # No trades

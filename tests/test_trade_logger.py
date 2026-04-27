"""
Integration tests for TradeLogger.
"""
import os
import pytest
from datetime import datetime, timezone
from src.core.trade_logger import TradeLogger, Trade, RiskEvent, Base

@pytest.fixture
def logger():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    # For tests, we use create_all to set up the schema quickly.
    Base.metadata.create_all(logger.engine)
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
    signal_id = logger.log_signal(signal_data, user="test_user")
    assert signal_id > 0

    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal
        signal = session.get(ModelSignal, signal_id)
        assert signal.created_by == "test_user"
        assert signal.entry_price == 2000.0

def test_log_trade(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    })
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        user="trader_1"
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.get(Trade, trade_id)
        assert trade.created_by == "trader_1"
        assert trade.ticket == 12345

def test_update_trade(logger):
    logger.log_trade(123, "XAUUSD", 1, 2000.0, 0.1)
    logger.update_trade(123, 2010.0, pnl=100.0, user="bot")

    trade = logger.get_trade_by_ticket(123)
    assert trade.status == "CLOSED"
    assert trade.exit_price == 2010.0
    assert trade.pnl == 100.0
    assert trade.updated_by == "bot"

def test_soft_delete(logger):
    logger.log_trade(456, "XAUUSD", 1, 2000.0, 0.1)
    logger.soft_delete_trade(456, user="admin")

    trade = logger.get_trade_by_ticket(456)
    assert trade is None

    with logger.Session() as session:
        from sqlalchemy import select
        stmt = select(Trade).where(Trade.ticket == 456)
        trade_in_db = session.execute(stmt).scalar_one()
        assert trade_in_db.is_deleted is True
        assert trade_in_db.deleted_at is not None
        assert trade_in_db.updated_by == "admin"

def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, pnl=100.0)

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, pnl=-50.0)

    report = logger.read_performance_report(user="analyst")
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    assert report["max_drawdown"] == 50.0

    with logger.Session() as session:
        from src.core.trade_logger import PerformanceMetric
        from sqlalchemy import select
        metric = session.execute(select(PerformanceMetric)).scalar_one()
        assert metric.profit_factor == 2.0
        assert metric.created_by == "analyst"

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit", user="risk_mgr")
    with logger.Session() as session:
        from sqlalchemy import select
        event = session.execute(select(RiskEvent)).scalar_one()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.created_by == "risk_mgr"

def test_check_constraints(logger):
    from sqlalchemy.exc import IntegrityError

    # Test entry_price > 0
    with pytest.raises(IntegrityError):
        # We need to use a separate session for each failing insert to avoid transaction state issues in some DBs,
        # but SQLAlchemy's Session with engine.begin() or explicit rollback handles it.
        try:
            logger.log_trade(ticket=999, symbol="XAUUSD", direction=1, entry_price=-10.0, lot_size=0.1)
        except IntegrityError:
            raise

    # Test lot_size > 0
    with pytest.raises(IntegrityError):
        try:
            logger.log_trade(ticket=888, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.0)
        except IntegrityError:
            raise

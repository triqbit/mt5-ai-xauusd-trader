"""
Integration tests for TradeLogger.
"""
import os
import pytest
from src.core.trade_logger import TradeLogger

@pytest.fixture
def logger():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
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
        "confidence": 0.8,
    }
    signal_id = logger.log_signal(signal_data, user="test_user")
    assert signal_id > 0

    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal

        signal = session.query(ModelSignal).filter(ModelSignal.id == signal_id).first()
        assert signal.created_by == "test_user"
        assert signal.symbol == "XAUUSD"


def test_log_trade(logger):
    signal_id = logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        user="trader_joe",
    )
    assert trade_id > 0

    with logger.Session() as session:
        from src.core.trade_logger import Trade

        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.created_by == "trader_joe"
        assert trade.ticket == 12345

def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0)

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, -50.0)

    report = logger.read_performance_report(user="reporter")
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    assert report["max_drawdown"] == 50.0

    with logger.Session() as session:
        from src.core.trade_logger import PerformanceMetric

        metric = session.query(PerformanceMetric).order_by(PerformanceMetric.id.desc()).first()
        assert metric.created_by == "reporter"

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit", user="risk_engine")
    # No exception means success, we could query DB to be sure
    with logger.Session() as session:
        from src.core.trade_logger import RiskEvent

        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.created_by == "risk_engine"


def test_log_rejected_trade(logger):
    # Rejected trade should have status='REJECTED' and no ticket
    trade_id = logger.log_trade(
        ticket=None,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="REJECTED",
        user="risk_engine",
    )
    assert trade_id > 0

    with logger.Session() as session:
        from src.core.trade_logger import Trade

        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.status == "REJECTED"
        assert trade.ticket is None


def test_constraints(logger):
    from sqlalchemy.exc import IntegrityError

    # Test entry_price > 0
    with pytest.raises(IntegrityError):
        logger.log_trade(ticket=999, symbol="XAUUSD", direction=1, entry_price=-10.0, lot_size=0.1)

    # Test lot_size > 0
    with pytest.raises(IntegrityError):
        logger.log_trade(ticket=888, symbol="XAUUSD", direction=1, entry_price=2000.0, lot_size=0.0)

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
    signal_id = logger.log_signal(signal_data, created_by="test_user")
    assert signal_id > 0
    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal

        signal = session.query(ModelSignal).filter(ModelSignal.id == signal_id).first()
        assert signal.created_by == "test_user"
        assert signal.created_at is not None


def test_log_trade(logger):
    signal_id = logger.log_signal(
        {"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0}
    )
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        created_by="test_trader",
    )
    assert trade_id > 0
    with logger.Session() as session:
        from src.core.trade_logger import Trade

        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.created_by == "test_trader"
        assert trade.status == "OPEN"


def test_log_rejected_trade(logger):
    trade_id = logger.log_trade(
        ticket=None,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="REJECTED",
    )
    assert trade_id > 0
    with logger.Session() as session:
        from src.core.trade_logger import Trade

        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.status == "REJECTED"
        assert trade.ticket is None

def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0, updated_by="closer")

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, -50.0)

    report = logger.read_performance_report()
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    assert report["max_drawdown"] == 50.0

    with logger.Session() as session:
        from src.core.trade_logger import Trade

        trade1 = session.query(Trade).filter(Trade.ticket == 1).first()
        assert trade1.updated_by == "closer"


def test_constraints(logger):
    from sqlalchemy.exc import IntegrityError

    # Test negative entry price
    with pytest.raises(IntegrityError):
        logger.log_trade(3, "XAUUSD", 1, -100.0, 0.1)

    # Test zero lot size
    with pytest.raises(IntegrityError):
        logger.log_trade(4, "XAUUSD", 1, 2000.0, 0.0)

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    # No exception means success, we could query DB to be sure
    with logger.Session() as session:
        from src.core.trade_logger import RiskEvent
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"

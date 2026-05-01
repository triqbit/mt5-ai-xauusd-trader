"""
Integration tests for TradeLogger.
"""

import os

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.trade_logger import ModelSignal, RiskEvent, Trade, TradeLogger


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
        "created_by": "test_user",
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

    with logger.Session() as session:
        signal = session.query(ModelSignal).filter_by(id=signal_id).first()
        assert signal.created_by == "test_user"
        assert signal.created_at is not None


def test_log_trade(logger):
    signal_id = logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
        created_by="executor",
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.query(Trade).filter_by(id=trade_id).first()
        assert trade.created_by == "executor"


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


def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit", created_by="risk_manager")
    with logger.Session() as session:
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.created_by == "risk_manager"


def test_constraints_signal(logger):
    # Test negative entry price
    with pytest.raises(IntegrityError):
        logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": -10.0})

    # Test invalid direction
    with pytest.raises(IntegrityError):
        logger.log_signal({"symbol": "XAUUSD", "direction": 5, "entry_price": 2000.0})


def test_constraints_trade(logger):
    # Test negative lot size
    with pytest.raises(IntegrityError):
        logger.log_trade(1, "XAUUSD", 1, 2000.0, -0.1)


def test_soft_delete(logger):
    logger.log_trade(123, "XAUUSD", 1, 2000.0, 0.1)
    success = logger.delete_trade(123, deleted_by="admin")
    assert success is True

    with logger.Session() as session:
        trade = session.query(Trade).filter_by(ticket=123).first()
        assert trade.is_deleted is True
        assert trade.deleted_at is not None
        assert trade.updated_by == "admin"

    # Should not be visible in performance report
    logger.update_trade(
        123, 2010.0, 100.0
    )  # This should actually not update if it checks is_deleted
    report = logger.read_performance_report()
    # If no trades are found, it returns the default report
    assert report["profit_factor"] == 0.0
    assert report["sharpe_ratio"] == 0.0
    assert report["max_drawdown"] == 0.0

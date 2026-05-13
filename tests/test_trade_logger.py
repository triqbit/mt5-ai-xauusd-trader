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
    from src.core.trade_logger import Base

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
        "confidence": 0.8,
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0


def test_log_trade(logger):
    signal_id = logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id,
    )
    assert trade_id > 0


def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0)

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, -50.0)

    report = logger.read_performance_report()
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    assert report["max_drawdown"] == 50.0
    assert "calmar_ratio" in report
    assert "expectancy" in report
    assert report["expectancy"] == 25.0  # (0.5 * 100) - (0.5 * 50)


def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    # No exception means success, we could query DB to be sure
    with logger.Session() as session:
        from src.core.trade_logger import RiskEvent

        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"


def test_audit_columns(logger):
    signal_id = logger.log_signal({"symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0})
    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal

        signal = session.get(ModelSignal, signal_id)
        assert signal.created_at is not None
        assert signal.updated_at is not None
        assert signal.is_deleted is False


def test_constraints(logger):
    from sqlalchemy.exc import IntegrityError

    # Test price constraint
    with pytest.raises(IntegrityError), logger.Session() as session:
        from src.core.trade_logger import ModelSignal

        bad_signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=-10.0,  # Should fail
        )
        session.add(bad_signal)
        session.commit()

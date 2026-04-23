"""
Integration tests for TradeLogger.
"""
import os
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from src.core.trade_logger import TradeLogger, ModelSignal, Trade, RiskEvent

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
        "lot_size": 0.1,
        "algorithm": "ppo",
        "confidence": 0.8
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

    with logger.Session() as session:
        signal = session.query(ModelSignal).filter(ModelSignal.id == signal_id).first()
        assert signal.symbol == "XAUUSD"
        assert signal.created_at is not None
        assert hasattr(signal, 'created_by')
        assert hasattr(signal, 'deleted_at')

def test_log_trade(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1
    })
    trade_id = logger.log_trade(
        ticket=12345,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.ticket == 12345
        assert trade.status == "OPEN"
        assert trade.created_at is not None

def test_log_rejected_trade(logger):
    trade_id = logger.log_trade(
        ticket=None,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="REJECTED"
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.query(Trade).filter(Trade.id == trade_id).first()
        assert trade.ticket is None
        assert trade.status == "REJECTED"

def test_check_constraints(logger):
    # Test negative entry price
    with pytest.raises(IntegrityError):
        with logger.Session() as session:
            signal = ModelSignal(
                symbol="XAUUSD",
                direction=1,
                entry_price=-10.0,
                lot_size=0.1
            )
            session.add(signal)
            session.commit()

    # Test negative lot size
    with pytest.raises(IntegrityError):
        with logger.Session() as session:
            trade = Trade(
                symbol="XAUUSD",
                direction=1,
                entry_price=2000.0,
                lot_size=-0.1
            )
            session.add(trade)
            session.commit()

def test_performance_report(logger):
    # Log some closed trades
    # P&L Calculation in update_trade: (exit - entry) * direction * lot_size * 100
    # Trade 1: (2010 - 2000) * 1 * 0.1 * 100 = 10 * 0.1 * 100 = 100.0
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, 100.0)

    # Trade 2: (1995 - 2000) * 1 * 0.1 * 100 = -5 * 0.1 * 100 = -50.0
    logger.log_trade(2, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 1995.0, -50.0)

    report = logger.read_performance_report()
    assert report["profit_factor"] == 2.0
    assert report["sharpe_ratio"] != 0
    # Equity: 0 -> 100 -> 50. Peak = 100. DD at end = 100 - 50 = 50.
    assert report["max_drawdown"] == 50.0

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit", symbol="XAUUSD")
    with logger.Session() as session:
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.symbol == "XAUUSD"
        assert event.created_at is not None

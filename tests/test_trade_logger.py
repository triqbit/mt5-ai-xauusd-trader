"""
Integration tests for TradeLogger.
"""
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.trade_logger import TradeLogger, Trade, ModelSignal, RiskEvent


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
        "confidence": 0.8
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

    with logger.Session() as session:
        signal = session.get(ModelSignal, signal_id)
        assert signal.symbol == "XAUUSD"
        assert signal.created_at is not None
        assert signal.is_deleted is False

def test_log_signal_invalid_price(logger):
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": -100.0,
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

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
        signal_id=signal_id
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.get(Trade, trade_id)
        assert trade.ticket == 12345
        assert trade.created_at is not None
        assert trade.is_deleted is False

def test_log_trade_invalid_lot_size(logger):
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=12345,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=-0.1,
        )

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
    assert report["win_rate"] == 0.5
    assert report["total_trades"] == 2

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    with logger.Session() as session:
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.created_at is not None

def test_audit_columns_presence(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    })
    with logger.Session() as session:
        signal = session.get(ModelSignal, signal_id)
        assert hasattr(signal, 'created_at')
        assert hasattr(signal, 'updated_at')
        assert hasattr(signal, 'created_by')
        assert hasattr(signal, 'updated_by')
        assert hasattr(signal, 'deleted_at')
        assert hasattr(signal, 'is_deleted')
        assert isinstance(signal.created_at, datetime)

"""
Integration tests for TradeLogger.
"""
import os
from datetime import datetime, timezone
import pytest
from src.core.trade_logger import TradeLogger, Trade, RiskEvent

@pytest.fixture
def logger():
    db_path = "test_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    # Re-initialize to ensure fresh DB for tests
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

def test_log_trade_executed(logger):
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
        signal_source="ppo",
        status="OPEN"
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.query(Trade).get(trade_id)
        assert trade.ticket == 12345
        assert trade.signal_source == "ppo"
        assert trade.entry_time is not None
        assert trade.created_at is not None

def test_log_trade_rejected(logger):
    trade_id = logger.log_trade(
        ticket=None, # Rejected trades might not have a ticket
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        status="REJECTED",
        signal_source="risk_manager"
    )
    assert trade_id > 0

    with logger.Session() as session:
        trade = session.query(Trade).get(trade_id)
        assert trade.ticket is None
        assert trade.status == "REJECTED"
        assert trade.signal_source == "risk_manager"

def test_performance_report(logger):
    # Log some closed trades
    logger.log_trade(1, "XAUUSD", 1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(1, 2010.0, pnl=100.0)

    logger.log_trade(2, "XAUUSD", -1, 2000.0, 0.1, status="OPEN")
    logger.update_trade(2, 2005.0, pnl=-50.0)

    report = logger.read_performance_report()
    assert report["profit_factor"] == 2.0
    # Sharpe ratio with 2 trades (100, -50):
    # mean=25, std=75. 25/75 * sqrt(252) ~= 5.29
    assert report["sharpe_ratio"] > 0
    assert report["max_drawdown"] == 50.0

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    with logger.Session() as session:
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"
        assert event.created_at is not None

def test_audit_columns(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    })
    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal
        signal = session.query(ModelSignal).get(signal_id)
        assert signal.created_at is not None
        assert signal.updated_at is not None
        assert signal.is_deleted is False

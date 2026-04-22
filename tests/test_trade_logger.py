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
        "confidence": 0.8
    }
    signal_id = logger.log_signal(signal_data)
    assert signal_id > 0

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

def test_log_risk_event(logger):
    logger.log_risk_event("CIRCUIT_BREAKER", "Drawdown limit hit")
    # No exception means success, we could query DB to be sure
    with logger.Session() as session:
        from src.core.trade_logger import RiskEvent
        event = session.query(RiskEvent).first()
        assert event.event_type == "CIRCUIT_BREAKER"

def test_log_rejected_trade(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1
    })
    logger.log_rejected_trade(signal_id, "Volatility too high")

    with logger.Session() as session:
        from src.core.trade_logger import Trade, RiskEvent
        trade = session.query(Trade).filter(Trade.status == "REJECTED").first()
        assert trade is not None
        assert trade.signal_id == signal_id

        event = session.query(RiskEvent).filter(RiskEvent.event_type == "TRADE_REJECTED").first()
        assert event is not None
        assert event.description == "Volatility too high"

def test_audit_columns(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
    })
    with logger.Session() as session:
        from src.core.trade_logger import ModelSignal
        signal = session.query(ModelSignal).filter(ModelSignal.id == signal_id).first()
        assert signal.created_at is not None
        assert signal.updated_at is not None

def test_constraints(logger):
    import sqlalchemy.exc
    # Invalid entry price
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        logger.log_signal({
            "symbol": "XAUUSD",
            "direction": 1,
            "entry_price": -100.0
        })

    # Invalid lot size (must be >= 0)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        logger.log_signal({
            "symbol": "XAUUSD",
            "direction": 1,
            "entry_price": 2000.0,
            "lot_size": -0.1
        })

def test_log_rejected_trade_no_lot(logger):
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0
        # lot_size missing
    })
    # Should not raise IntegrityError even though lot_size will be 0.0
    logger.log_rejected_trade(signal_id, "Filter check failed")

    with logger.Session() as session:
        from src.core.trade_logger import Trade
        trade = session.query(Trade).filter(Trade.status == "REJECTED").first()
        assert trade is not None
        assert trade.lot_size == 0.0

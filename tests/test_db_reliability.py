"""
Targeted tests for database reliability improvements.
"""
import os
import pytest
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from src.core.trade_logger import TradeLogger, Trade, ModelSignal

@pytest.fixture
def logger():
    db_path = "test_reliability.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_check_constraints(logger):
    """Verify that CheckConstraints prevent invalid data."""
    # Test negative entry price in ModelSignal
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": -100.0, # Invalid
        "lot_size": 0.1,
        "confidence": 0.8
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

    # Test invalid confidence
    signal_data["entry_price"] = 2000.0
    signal_data["confidence"] = 1.5 # Invalid (>1)
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

    # Test negative entry price in Trade
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=1,
            symbol="XAUUSD",
            direction=1,
            entry_price=-2000.0, # Invalid
            lot_size=0.1
        )

def test_soft_delete_filtering(logger):
    """Verify that is_deleted=True records are excluded from queries."""
    ticket = 55555
    logger.log_trade(
        ticket=ticket,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1
    )

    # Manually set is_deleted = True
    with logger.Session.begin() as session:
        stmt = select(Trade).where(Trade.ticket == ticket)
        trade = session.execute(stmt).scalar_one()
        trade.is_deleted = True

    # get_trade_by_ticket should return None
    assert logger.get_trade_by_ticket(ticket) is None

    # update_trade should not find it
    logger.update_trade(ticket, 2010.0) # Should log warning, not crash

def test_transaction_atomicity(logger):
    """Verify that a failure in a transaction results in a rollback."""
    # We'll use log_signal as it's a simple transaction
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1,
        "confidence": 0.8
    }

    # First, a valid log
    sig_id = logger.log_signal(signal_data)
    assert sig_id is not None

    # Now, try to log something that will fail (e.g. invalid price)
    # but we want to see if it affects anything else.
    # Actually, logger.Session.begin() ensures the whole block is atomic.

    with pytest.raises(IntegrityError):
        with logger.Session.begin() as session:
            s1 = ModelSignal(symbol="X1", direction=1, entry_price=100, lot_size=0.1, confidence=0.5)
            session.add(s1)
            # s2 will fail due to CheckConstraint
            s2 = ModelSignal(symbol="X2", direction=1, entry_price=-100, lot_size=0.1, confidence=0.5)
            session.add(s2)

    # Verify s1 was NOT committed
    with logger.Session() as session:
        stmt = select(ModelSignal).where(ModelSignal.symbol == "X1")
        res = session.execute(stmt).scalar_one_or_none()
        assert res is None

"""
Tests for Database Integrity Constraints.
"""
import os
import pytest
from sqlalchemy.exc import IntegrityError
from src.core.trade_logger import TradeLogger, ModelSignal, Trade

@pytest.fixture
def logger():
    db_path = "test_integrity.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    # Important: SQLite doesn't always enforce CHECK constraints by default,
    # but SQLAlchemy's create_all with the defined models will include them.
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_signal_entry_price_positive(logger):
    with logger.Session() as session:
        # Invalid entry price
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=-10.0,
            lot_size=0.1,
            confidence=0.8
        )
        session.add(signal)
        with pytest.raises(IntegrityError):
            session.commit()

def test_signal_lot_size_positive(logger):
    with logger.Session() as session:
        # Invalid lot size
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=-0.1,
            confidence=0.8
        )
        session.add(signal)
        with pytest.raises(IntegrityError):
            session.commit()

def test_signal_confidence_range(logger):
    with logger.Session() as session:
        # Invalid confidence (> 1)
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            confidence=1.5
        )
        session.add(signal)
        with pytest.raises(IntegrityError):
            session.commit()

def test_trade_entry_price_positive(logger):
    with logger.Session() as session:
        trade = Trade(
            ticket=999,
            symbol="XAUUSD",
            direction=1,
            entry_price=0.0,  # Should be > 0
            lot_size=0.1
        )
        session.add(trade)
        with pytest.raises(IntegrityError):
            session.commit()

def test_trade_lot_size_positive(logger):
    with logger.Session() as session:
        trade = Trade(
            ticket=999,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.0
        )
        session.add(trade)
        with pytest.raises(IntegrityError):
            session.commit()

def test_valid_data(logger):
    with logger.Session() as session:
        signal = ModelSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=0.1,
            confidence=0.8
        )
        session.add(signal)
        session.commit()
        assert signal.id is not None

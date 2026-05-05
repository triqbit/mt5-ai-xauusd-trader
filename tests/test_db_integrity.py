"""
Tests for database integrity constraints.
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
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_signal_entry_price_constraint(logger):
    """Verify that entry_price > 0 for signals."""
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": -100.0,  # Invalid
        "lot_size": 0.1,
        "confidence": 0.8
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

def test_signal_lot_size_constraint(logger):
    """Verify that lot_size > 0 for signals."""
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.0,  # Invalid
        "confidence": 0.8
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

def test_signal_confidence_constraint(logger):
    """Verify that 0 <= confidence <= 1 for signals."""
    # Test confidence > 1
    signal_data_high = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1,
        "confidence": 1.1  # Invalid
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data_high)

    # Test confidence < 0
    signal_data_low = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1,
        "confidence": -0.1  # Invalid
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data_low)

def test_trade_entry_price_constraint(logger):
    """Verify that entry_price > 0 for trades."""
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=123,
            symbol="XAUUSD",
            direction=1,
            entry_price=0.0,  # Invalid
            lot_size=0.1
        )

def test_trade_lot_size_constraint(logger):
    """Verify that lot_size > 0 for trades."""
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=124,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=-0.5  # Invalid
        )

def test_valid_data_works(logger):
    """Verify that valid data is accepted."""
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "lot_size": 0.1,
        "confidence": 0.9
    })
    assert signal_id > 0

    trade_id = logger.log_trade(
        ticket=125,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id
    )
    assert trade_id > 0

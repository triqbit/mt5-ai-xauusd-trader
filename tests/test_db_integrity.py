"""
Unit tests for Database Integrity constraints.
"""
import os
import pytest
from sqlalchemy.exc import IntegrityError
from src.core.trade_logger import TradeLogger

@pytest.fixture
def logger():
    db_path = "test_integrity.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    # create_all is called in __init__
    logger = TradeLogger(db_url=f"sqlite:///{db_path}")
    yield logger
    if os.path.exists(db_path):
        os.remove(db_path)

def test_signal_entry_price_positive(logger):
    """Test that entry_price must be > 0 for signals."""
    signal_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": -100.0,  # Invalid
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data)

def test_signal_confidence_range(logger):
    """Test that confidence must be between 0 and 1."""
    # Too high
    signal_data_high = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "confidence": 1.5
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data_high)

    # Too low
    signal_data_low = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "confidence": -0.1
    }
    with pytest.raises(IntegrityError):
        logger.log_signal(signal_data_low)

def test_trade_entry_price_positive(logger):
    """Test that entry_price must be > 0 for trades."""
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=1,
            symbol="XAUUSD",
            direction=1,
            entry_price=0.0,  # Invalid
            lot_size=0.1
        )

def test_trade_lot_size_positive(logger):
    """Test that lot_size must be > 0 for trades."""
    with pytest.raises(IntegrityError):
        logger.log_trade(
            ticket=2,
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            lot_size=-0.01  # Invalid
        )

def test_successful_entries(logger):
    """Verify that valid data is still accepted."""
    signal_id = logger.log_signal({
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "confidence": 0.9
    })
    assert signal_id > 0

    trade_id = logger.log_trade(
        ticket=100,
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        lot_size=0.1,
        signal_id=signal_id
    )
    assert trade_id > 0

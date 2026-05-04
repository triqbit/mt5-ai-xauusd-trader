"""
Tests for TradeSignal schema and internal validation.
"""
import pytest
from datetime import datetime
from src.trading.risk_manager import TradeSignal

def test_valid_signal():
    """Test that a valid signal is created successfully."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == 1
    assert signal.confidence == 0.8

def test_invalid_direction():
    """Test that an invalid direction raises ValueError."""
    with pytest.raises(ValueError, match="Invalid direction"):
        TradeSignal(
            symbol="XAUUSD",
            direction=2,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )

def test_invalid_entry_price():
    """Test that an invalid entry price raises ValueError."""
    with pytest.raises(ValueError, match="Invalid entry price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=0.0,
            stop_loss=-10,
            take_profit=10,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )

def test_invalid_confidence():
    """Test that confidence out of bounds raises ValueError."""
    with pytest.raises(ValueError, match="Invalid confidence"):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=1.1
        )

def test_invalid_lot_size():
    """Test that negative lot size raises ValueError."""
    with pytest.raises(ValueError, match="Invalid lot size"):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=-0.1,
            algorithm="ensemble",
            confidence=0.8
        )

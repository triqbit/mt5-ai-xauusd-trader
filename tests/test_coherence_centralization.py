"""
Tests for centralized domain types and coherence improvements.
Ensures that SignalDirection, TradeSignal, and ExecutionDecision are correctly centralized and validated.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.core.types import ExecutionDecision, SignalDirection, TradeSignal


def test_signal_direction_enum():
    """Verify SignalDirection enum values."""
    assert SignalDirection.BUY == 1
    assert SignalDirection.SELL == -1
    assert SignalDirection.HOLD == 0

def test_trade_signal_validation():
    """Verify TradeSignal Pydantic validation."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2250.0,
        take_profit=2400.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == 1
    assert isinstance(signal.timestamp, datetime)
    assert signal.timestamp.tzinfo == timezone.utc

def test_trade_signal_invalid_lot_size():
    """Verify that lot_size < 0.01 raises ValidationError."""
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2300.0,
            stop_loss=2250.0,
            take_profit=2400.0,
            lot_size=0.005,  # Below 0.01
            algorithm="ensemble",
            confidence=0.85
        )

def test_execution_decision_composition():
    """Verify ExecutionDecision contains a TradeSignal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2250.0,
        take_profit=2400.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    decision = ExecutionDecision(
        signal=signal,
        is_approved=True,
        confidence_score=0.9
    )
    assert decision.signal.symbol == "XAUUSD"
    assert decision.is_approved is True

def test_signal_direction_parsing():
    """Verify that integer values are correctly parsed into SignalDirection enum."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=-1,  # Should be parsed to SignalDirection.SELL
        entry_price=2300.0,
        stop_loss=2350.0,
        take_profit=2200.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert isinstance(signal.direction, SignalDirection)
    assert signal.direction == SignalDirection.SELL

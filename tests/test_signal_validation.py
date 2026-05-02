"""
Unit tests for TradeSignal schema validation.
tests/test_signal_validation.py
"""

import pytest
from pydantic import ValidationError
from src.trading.risk_manager import TradeSignal
from src.core.constants import SignalDirection

def test_valid_buy_signal():
    """Verify a standard valid BUY signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == SignalDirection.BUY

def test_valid_sell_signal():
    """Verify a standard valid SELL signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.SELL,
        entry_price=2300.0,
        stop_loss=2310.0,
        take_profit=2280.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert signal.direction == SignalDirection.SELL

def test_invalid_direction_hold():
    """TradeSignal should not accept HOLD direction."""
    with pytest.raises(ValidationError, match="TradeSignal cannot have HOLD direction"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.HOLD,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

def test_invalid_confidence_range():
    """Confidence must be between 0 and 1."""
    with pytest.raises(ValidationError, match="Input should be less than or equal to 1"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="test",
            confidence=1.1
        )

def test_negative_financial_values():
    """Entry price, SL, TP, and lot size must be positive."""
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=-1.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

def test_buy_invalid_sl_above_entry():
    """In a BUY, stop_loss must be below entry_price."""
    with pytest.raises(ValidationError, match="BUY stop_loss must be below entry_price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2310.0,
            take_profit=2350.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

def test_buy_invalid_tp_below_entry():
    """In a BUY, take_profit must be above entry_price."""
    with pytest.raises(ValidationError, match="BUY take_profit must be above entry_price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2280.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

def test_sell_invalid_sl_below_entry():
    """In a SELL, stop_loss must be above entry_price."""
    with pytest.raises(ValidationError, match="SELL stop_loss must be above entry_price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.SELL,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2250.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

def test_sell_invalid_tp_above_entry():
    """In a SELL, take_profit must be below entry_price."""
    with pytest.raises(ValidationError, match="SELL take_profit must be below entry_price"):
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.SELL,
            entry_price=2300.0,
            stop_loss=2310.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="test",
            confidence=0.9
        )

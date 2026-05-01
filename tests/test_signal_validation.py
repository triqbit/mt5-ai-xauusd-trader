"""Tests for TradeSignal validation."""
import pytest
from pydantic import ValidationError
from src.trading.risk_manager import TradeSignal
from src.core.exceptions import RiskValidationError

def test_valid_buy_signal():
    """Test a valid BUY signal."""
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

def test_valid_sell_signal():
    """Test a valid SELL signal."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=-1,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1980.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )
    assert signal.direction == -1

def test_invalid_direction():
    """Test invalid direction (not 1 or -1)."""
    with pytest.raises(RiskValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=0,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )
    assert "Invalid direction" in str(exc.value)

def test_invalid_buy_prices():
    """Test invalid BUY prices (SL above entry or TP below entry)."""
    # SL above entry
    with pytest.raises(RiskValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=2010.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )
    assert "Stop loss" in str(exc.value)

    # TP below entry
    with pytest.raises(RiskValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=1980.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )
    assert "Take profit" in str(exc.value)

def test_invalid_sell_prices():
    """Test invalid SELL prices (SL below entry or TP above entry)."""
    # SL below entry
    with pytest.raises(RiskValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=-1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=1980.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )
    assert "Stop loss" in str(exc.value)

    # TP above entry
    with pytest.raises(RiskValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=-1,
            entry_price=2000.0,
            stop_loss=2010.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.8
        )
    assert "Take profit" in str(exc.value)

def test_invalid_confidence():
    """Test invalid confidence range."""
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=1,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=1.5
        )

def test_missing_fields():
    """Test validation fails when required fields are missing."""
    with pytest.raises(ValidationError):
        TradeSignal(
            symbol="XAUUSD",
            direction=1
            # Missing other fields
        )

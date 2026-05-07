
import pytest
from pydantic import ValidationError

from src.core.schemas import SignalDirection, TradeSignal


def test_trade_signal_schema_valid():
    """Verify that a valid signal data dictionary passes validation."""
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2300.0,
        "stop_loss": 2250.0,
        "take_profit": 2400.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.85
    }
    signal = TradeSignal(**data)
    assert signal.symbol == "XAUUSD"
    assert signal.direction == SignalDirection.BUY
    assert signal.entry_price == 2300.0
    assert signal.lot_size == 0.1

def test_trade_signal_schema_enum_parsing():
    """Verify that integer directions are correctly parsed into SignalDirection enums."""
    assert TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300, stop_loss=2250,
        take_profit=2400, lot_size=0.1, algorithm="test", confidence=0.9
    ).direction == SignalDirection.BUY

    assert TradeSignal(
        symbol="XAUUSD", direction=-1, entry_price=2300, stop_loss=2350,
        take_profit=2200, lot_size=0.1, algorithm="test", confidence=0.9
    ).direction == SignalDirection.SELL

@pytest.mark.parametrize("field, value", [
    ("direction", 2),
    ("direction", -2),
    ("entry_price", -1.0),
    ("entry_price", 0.0),
    ("stop_loss", -50.0),
    ("take_profit", 0.0),
    ("lot_size", 0.005),
    ("confidence", -0.1),
    ("confidence", 1.1),
    ("symbol", "X"),
    ("symbol", "XAUUSD!"),
    ("symbol", "this_is_too_long_for_the_schema"),
])
def test_trade_signal_schema_invalid_values(field, value):
    """Verify that invalid values raise ValidationError."""
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2300.0,
        "stop_loss": 2250.0,
        "take_profit": 2400.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.85
    }
    data[field] = value
    with pytest.raises(ValidationError):
        TradeSignal(**data)

def test_buy_price_boundaries():
    """Verify BUY boundary validation (SL < Entry < TP) and R:R."""
    base = {
        "symbol": "XAUUSD", "direction": 1, "entry_price": 2000.0,
        "lot_size": 0.1, "algorithm": "test", "confidence": 0.9
    }

    # Valid (Reward=300, Risk=100, RR=3.0)
    TradeSignal(**base, stop_loss=1900, take_profit=2300)

    # Invalid R:R (Reward=50, Risk=100, RR=0.5)
    with pytest.raises(ValidationError, match="Risk-Reward ratio"):
        TradeSignal(**base, stop_loss=1900, take_profit=2050)

    # Invalid SL
    with pytest.raises(ValidationError, match="BUY Stop Loss"):
        TradeSignal(**base, stop_loss=2050, take_profit=2300)

    # Invalid TP (Higher than entry, but RR < 1.5)
    with pytest.raises(ValidationError, match="Risk-Reward ratio"):
        TradeSignal(**base, stop_loss=1900, take_profit=2050)

    # Invalid TP (Lower than entry, but RR is valid)
    # Risk = 100, Reward = 200 (RR=2.0)
    with pytest.raises(ValidationError, match="BUY Take Profit"):
        TradeSignal(**base, stop_loss=1900, take_profit=1800)

def test_sell_price_boundaries():
    """Verify SELL boundary validation (SL > Entry > TP) and R:R."""
    base = {
        "symbol": "XAUUSD", "direction": -1, "entry_price": 2000.0,
        "lot_size": 0.1, "algorithm": "test", "confidence": 0.9
    }

    # Valid (Reward=300, Risk=100, RR=3.0)
    TradeSignal(**base, stop_loss=2100, take_profit=1700)

    # Invalid R:R (Reward=50, Risk=100, RR=0.5)
    with pytest.raises(ValidationError, match="Risk-Reward ratio"):
        TradeSignal(**base, stop_loss=2100, take_profit=1950)

    # Invalid SL
    with pytest.raises(ValidationError, match="SELL Stop Loss"):
        TradeSignal(**base, stop_loss=1950, take_profit=1700)

    # Invalid TP (Lower than entry, but RR < 1.5)
    with pytest.raises(ValidationError, match="Risk-Reward ratio"):
        TradeSignal(**base, stop_loss=2100, take_profit=1950)

    # Invalid TP (Higher than entry, but RR is valid)
    # Risk = 100, Reward = 200 (RR=2.0)
    with pytest.raises(ValidationError, match="SELL Take Profit"):
        TradeSignal(**base, stop_loss=2100, take_profit=2200)

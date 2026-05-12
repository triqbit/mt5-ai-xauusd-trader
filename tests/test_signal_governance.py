import pytest
from pydantic import ValidationError
from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.core.schemas import TradeSignal

def test_signal_validation():
    """Verify that the core Signal model enforces its constraints."""
    # Valid signal
    sig = Signal(direction=SignalDirection.BUY, confidence=0.85)
    assert sig.direction == SignalDirection.BUY
    assert sig.confidence == 0.85
    assert sig.metadata is None

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        Signal(direction=SignalDirection.BUY, confidence=1.1)

    # Invalid confidence (too low)
    with pytest.raises(ValidationError):
        Signal(direction=SignalDirection.SELL, confidence=-0.1)

    # Immutability (frozen=True)
    with pytest.raises(ValidationError): # Pydantic v2 raises ValidationError on assignment to frozen
        sig.confidence = 0.9

def test_trade_signal_algorithm_governance():
    """Verify that TradeSignal only accepts supported algorithms."""
    base_data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "take_profit": 2020.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.8
    }

    # Valid algorithm
    ts = TradeSignal(**base_data)
    assert ts.algorithm == "ensemble"

    # Invalid algorithm
    invalid_data = base_data.copy()
    invalid_data["algorithm"] = "unsupported_ai"
    with pytest.raises(ValidationError):
        TradeSignal(**invalid_data)

def test_signal_asdict_backward_compatibility():
    """Ensure _asdict() still works for existing code."""
    sig = Signal(direction=SignalDirection.HOLD, confidence=0.5, metadata={"test": True})
    data = sig._asdict()
    assert isinstance(data, dict)
    assert data["direction"] == SignalDirection.HOLD
    assert data["confidence"] == 0.5
    assert data["metadata"] == {"test": True}

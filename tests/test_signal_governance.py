"""
Tests for Signal governance and validation.
"""

import pytest
from pydantic import ValidationError

from src.core.constants import SignalDirection
from src.models.base_model import Signal


def test_signal_valid():
    """Verify valid Signal instantiation."""
    sig = Signal(direction=SignalDirection.BUY, confidence=0.85)
    assert sig.direction == SignalDirection.BUY
    assert sig.confidence == 0.85
    assert sig._asdict()["confidence"] == 0.85

def test_signal_invalid_confidence_low():
    """Verify confidence >= 0.0 enforcement."""
    with pytest.raises(ValidationError):
        Signal(direction=SignalDirection.BUY, confidence=-0.1)

def test_signal_invalid_confidence_high():
    """Verify confidence <= 1.0 enforcement."""
    with pytest.raises(ValidationError):
        Signal(direction=SignalDirection.BUY, confidence=1.1)

def test_signal_frozen():
    """Verify Signal is immutable."""
    sig = Signal(direction=SignalDirection.BUY, confidence=0.85)
    with pytest.raises(ValidationError):
        sig.confidence = 0.90 # type: ignore

def test_signal_extra_forbid():
    """Verify Signal forbids extra fields."""
    with pytest.raises(ValidationError):
        Signal(direction=SignalDirection.BUY, confidence=0.85, extra="untrusted") # type: ignore

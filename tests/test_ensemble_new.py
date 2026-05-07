"""Tests for src.models.ensemble module."""
import pytest
from src.models.ensemble import EnsembleModel
from src.models.base_model import Signal
from src.core.constants import SignalDirection

def test_ensemble_dissent():
    ensemble = EnsembleModel()
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
        "lstm": Signal(direction=SignalDirection.SELL, confidence=0.9)
    }
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD
    assert result.metadata["reason"] == "Dissent conflict"

def test_ensemble_consensus_buy():
    ensemble = EnsembleModel(model_weights={"ppo": 1.0, "lstm": 1.0, "dreamer": 1.0})
    # Set weights explicitly to ensure ppo is 1.0 for testing
    ensemble.dynamic_ensemble.weights = {"ppo": 1.0, "lstm": 0.0, "dreamer": 0.0}
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.7)
    }
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.BUY
    assert result.confidence == 0.7

def test_ensemble_no_consensus():
    ensemble = EnsembleModel(model_weights={"ppo": 1.0, "lstm": 1.0, "dreamer": 1.0})
    ensemble.dynamic_ensemble.weights = {"ppo": 1.0, "lstm": 0.0, "dreamer": 0.0}
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.5) # Below default 0.6
    }
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD

def test_ensemble_weighted_average():
    ensemble = EnsembleModel(model_weights={"ppo": 0.6, "lstm": 0.4, "dreamer": 0.0})
    # Weights should be normalized if they weren't already
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.5)
    }
    result = ensemble.aggregate_signals(signals)
    # Weighted confidence: 0.8 * 0.6 + 0.5 * 0.4 = 0.48 + 0.20 = 0.68
    assert result.direction == SignalDirection.BUY
    assert result.confidence == pytest.approx(0.68)

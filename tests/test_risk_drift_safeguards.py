import pytest
import numpy as np
from unittest.mock import MagicMock
from src.models.ensemble import EnsembleModel
from src.models.base_model import Signal
from src.core.constants import SignalDirection

@pytest.fixture
def ensemble():
    cfg = MagicMock()
    cfg.model_drift_threshold = 0.3
    model = EnsembleModel(config=cfg)
    # Mock weights
    model.dynamic_ensemble.weights = {"ppo": 0.4, "dreamer": 0.3, "lstm": 0.3}
    return model

def test_veto_power(ensemble):
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.35), # This should trigger veto
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.7)
    }

    result = ensemble.aggregate_signals(signals, symbol="XAUUSD")
    assert result.direction == SignalDirection.HOLD
    assert result.confidence == 0.0
    assert result.metadata["veto_active"] is True
    assert result.metadata["veto_model"] == "dreamer"

def test_drift_penalty(ensemble):
    # Mock health metrics to trigger drift penalty
    # penalty_trigger = 0.3 * 0.5 = 0.15
    # drift = 0.225 (midway between trigger and threshold for ~10% penalty)
    ensemble.get_health_metrics = MagicMock(return_value={"drift": 0.225, "accuracy": 0.6})

    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.8),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.8)
    }

    # consensus_threshold is 0.6
    result = ensemble.aggregate_signals(signals, symbol="XAUUSD")
    assert result.direction == SignalDirection.BUY
    # Confidence was 0.8, should be reduced
    assert result.confidence < 0.8
    assert "drift_penalty" in result.metadata

def test_entropy_guard(ensemble):
    # Standard deviation of [0.9, 0.4, 0.9] is ~0.235 (just below 0.25)
    # Let's use [0.9, 0.3, 0.9] -> std is ~0.28 (> 0.25)
    # Wait, 0.3 triggers veto!
    # Let's use [0.9, 0.4, 0.4] -> mean 0.56 (below consensus 0.6)

    # We need to bypass veto, so all >= 0.4
    # signals: [0.9, 0.4, 0.9]
    # mean: 0.9*0.4 + 0.4*0.3 + 0.9*0.3 = 0.36 + 0.12 + 0.27 = 0.75
    # std([0.9, 0.4, 0.9])
    vals = [0.9, 0.4, 0.9]
    std = np.std(vals)
    # std is ~0.235

    # Try [1.0, 0.4, 0.4]
    # mean: 1.0*0.4 + 0.4*0.3 + 0.4*0.3 = 0.4 + 0.12 + 0.12 = 0.64 (> 0.6)
    # std([1.0, 0.4, 0.4]) = 0.2828 (> 0.25)

    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=1.0),
        "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.4),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.4)
    }

    result = ensemble.aggregate_signals(signals, symbol="XAUUSD")
    assert result.direction == SignalDirection.BUY
    # Confidence should be penalized by 10%
    # Original weighted conf = 0.64. After 10% penalty = 0.576
    assert pytest.approx(result.confidence) == 0.64 * 0.9
    assert result.metadata["entropy_penalty"] == 0.10

def test_consensus_hold(ensemble):
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.5),
        "dreamer": Signal(direction=SignalDirection.BUY, confidence=0.5),
        "lstm": Signal(direction=SignalDirection.BUY, confidence=0.5)
    }
    # Weighted mean 0.5 < consensus_threshold 0.6
    result = ensemble.aggregate_signals(signals, symbol="XAUUSD")
    assert result.direction == SignalDirection.HOLD

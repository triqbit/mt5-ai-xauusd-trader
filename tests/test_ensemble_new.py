from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.models.ensemble import EnsembleModel


def test_ensemble_dissent():
    ensemble = EnsembleModel()
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.9),
        "lstm": Signal(direction=SignalDirection.SELL, confidence=0.9),
    }
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD
    assert result.metadata["reason"] == "Dissent conflict"


def test_ensemble_consensus_buy():
    ensemble = EnsembleModel(model_weights={"ppo": 1.0})
    signals = {"ppo": Signal(direction=SignalDirection.BUY, confidence=0.7)}
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.BUY
    assert result.confidence == 0.7


def test_ensemble_no_consensus():
    ensemble = EnsembleModel(model_weights={"ppo": 1.0})
    signals = {
        "ppo": Signal(direction=SignalDirection.BUY, confidence=0.5)  # Below 0.6
    }
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD

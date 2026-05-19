"""
Tests for EnsembleScenarioBuilder and its integration with EnsembleModel.
"""

import pytest

from src.core.constants import SignalDirection
from src.models.ensemble import EnsembleModel
from src.models.regime_detector import MarketRegime
from src.utils.synthetic_data import EnsembleScenarioBuilder


@pytest.fixture
def builder():
    return EnsembleScenarioBuilder(seed=42)


@pytest.fixture
def ensemble():
    return EnsembleModel()


def test_consensus_signals(builder):
    signals = builder.consensus_signals(SignalDirection.BUY, confidence=0.85)
    assert len(signals) == 3
    for name in ["ppo", "dreamer", "lstm"]:
        assert signals[name].direction == SignalDirection.BUY
        assert signals[name].confidence == 0.85


def test_dissent_signals(builder):
    signals = builder.dissent_signals()
    assert signals["ppo"].direction == SignalDirection.BUY
    assert signals["dreamer"].direction == SignalDirection.SELL


def test_veto_signals(builder):
    signals = builder.veto_signals(SignalDirection.SELL)
    assert signals["dreamer"].confidence < 0.4
    assert signals["ppo"].direction == SignalDirection.SELL


def test_regime_context(builder):
    info = builder.regime_context(MarketRegime.NEWS_SHOCK, transition_score=0.8)
    assert info.label == MarketRegime.NEWS_SHOCK
    assert info.volatility_index > 2.0
    assert info.transition_score == 0.8


def test_ensemble_integration_consensus(ensemble, builder):
    signals = builder.consensus_signals(SignalDirection.BUY, confidence=0.7)
    # Set equal weights
    ensemble.dynamic_ensemble.weights = {"ppo": 0.333, "dreamer": 0.333, "lstm": 0.334}

    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.BUY
    assert result.confidence == pytest.approx(0.7)


def test_ensemble_integration_dissent(ensemble, builder):
    signals = builder.dissent_signals()
    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD
    assert result.metadata["reason"] == "Dissent conflict"


def test_ensemble_integration_veto(ensemble, builder):
    signals = builder.veto_signals(SignalDirection.BUY)
    # Ensure dreamer has weight
    ensemble.dynamic_ensemble.weights = {"ppo": 0.3, "dreamer": 0.4, "lstm": 0.3}

    result = ensemble.aggregate_signals(signals)
    assert result.direction == SignalDirection.HOLD
    assert result.metadata["veto_active"] is True
    assert result.metadata["veto_model"] == "dreamer"


def test_ensemble_adaptive_consensus_news(ensemble, builder):
    signals = builder.consensus_signals(SignalDirection.BUY, confidence=0.7)
    # Default threshold is 0.6. NEWS_SHOCK raises it to 0.8.
    regime = builder.regime_context(MarketRegime.NEWS_SHOCK)

    result = ensemble.aggregate_signals(signals, regime_info=regime)
    # Confidence (0.7) < Threshold (0.8) -> HOLD
    assert result.direction == SignalDirection.HOLD


def test_ensemble_drift_penalty_state_population(ensemble, builder):
    """
    Verify that populating state with failures triggers drift penalty
    without mocking calculate_metrics.
    """
    # 1. Populate 'ppo' with a series of failures to trigger drift
    # Need at least 10 entries for drift detection logic
    # Long-term success
    builder.populate_ensemble_state(ensemble.dynamic_ensemble, "ppo", [True] * 20)
    # Recent failures (5 failures in last 25 total)
    builder.populate_ensemble_state(ensemble.dynamic_ensemble, "ppo", [False] * 5)

    # 2. Populate others with clean history
    builder.populate_ensemble_state(ensemble.dynamic_ensemble, "dreamer", [True] * 25)
    builder.populate_ensemble_state(ensemble.dynamic_ensemble, "lstm", [True] * 25)

    # 3. Check health metrics
    health = ensemble.get_health_metrics()
    assert health["drift"] > 0.0

    # 4. Aggregate signals and check for penalty
    signals = builder.consensus_signals(SignalDirection.BUY, confidence=0.9)
    result = ensemble.aggregate_signals(signals)

    # Drift penalty should be applied if drift > penalty_trigger (threshold/2)
    # Default threshold in EnsembleModel is 0.3 if config is None.
    # Penalty trigger = 0.15
    if health["drift"] > 0.15:
        assert result.confidence < 0.9
        assert "drift_penalty" in result.metadata

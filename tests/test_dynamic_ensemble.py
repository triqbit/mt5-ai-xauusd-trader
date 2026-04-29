"""
Tests for DynamicWeightAdapter and ensemble adaptation logic.
"""
import pytest
import numpy as np
from src.models.dynamic_ensemble import (
    DynamicWeightAdapter,
    MarketContext,
    MarketRegime,
    ModelPerformance,
)

def test_weight_initialization():
    algorithms = ["ppo", "dreamer", "lstm"]
    adapter = DynamicWeightAdapter(algorithms)

    assert len(adapter.current_weights) == 3
    assert pytest.approx(sum(adapter.current_weights.values())) == 1.0
    for alg in algorithms:
        assert pytest.approx(adapter.current_weights[alg]) == 1/3

def test_weight_normalization_with_min_weight():
    algorithms = ["ppo", "dreamer"]
    # Force one weight to be very small
    base_weights = {"ppo": 0.99, "dreamer": 0.01}
    adapter = DynamicWeightAdapter(algorithms, base_weights=base_weights, min_weight=0.05)

    assert adapter.current_weights["dreamer"] >= 0.05
    assert pytest.approx(sum(adapter.current_weights.values())) == 1.0

def test_regime_affinity_impact():
    algorithms = ["ppo", "lstm"]
    adapter = DynamicWeightAdapter(algorithms, ema_alpha=1.0) # Full update for testing

    # Set high affinity for ppo in TRENDING
    adapter.set_regime_affinity(MarketRegime.TRENDING, {"ppo": 2.0, "lstm": 1.0})

    context = MarketContext(regime=MarketRegime.TRENDING)
    perf = {alg: ModelPerformance(accuracy=0.5) for alg in algorithms}

    new_weights = adapter.get_weights(context, perf)

    assert new_weights["ppo"] > new_weights["lstm"]
    assert pytest.approx(sum(new_weights.values())) == 1.0

def test_accuracy_impact():
    algorithms = ["ppo", "lstm"]
    adapter = DynamicWeightAdapter(algorithms, ema_alpha=1.0)

    context = MarketContext(regime=MarketRegime.UNKNOWN)
    perf = {
        "ppo": ModelPerformance(accuracy=0.8),
        "lstm": ModelPerformance(accuracy=0.4)
    }

    new_weights = adapter.get_weights(context, perf)
    assert new_weights["ppo"] > new_weights["lstm"]

def test_drift_penalty():
    algorithms = ["ppo", "lstm"]
    adapter = DynamicWeightAdapter(algorithms, ema_alpha=1.0)

    context = MarketContext(regime=MarketRegime.UNKNOWN)
    perf = {
        "ppo": ModelPerformance(accuracy=0.5, drift_signal=0.5), # High drift
        "lstm": ModelPerformance(accuracy=0.5, drift_signal=0.0)  # No drift
    }

    new_weights = adapter.get_weights(context, perf)
    assert new_weights["lstm"] > new_weights["ppo"]

def test_ema_and_clipping_stability():
    algorithms = ["ppo", "lstm"]
    # Small alpha and small max_swing
    adapter = DynamicWeightAdapter(algorithms, ema_alpha=0.1, max_swing=0.01)

    initial_ppo_weight = adapter.current_weights["ppo"]

    # Try to force a huge change
    context = MarketContext(regime=MarketRegime.UNKNOWN)
    perf = {
        "ppo": ModelPerformance(accuracy=1.0),
        "lstm": ModelPerformance(accuracy=0.0)
    }

    new_weights = adapter.get_weights(context, perf)

    # Change should be very small due to max_swing and ema_alpha
    # max_delta = max_swing * ema_alpha = 0.01 * 0.1 = 0.001
    assert abs(new_weights["ppo"] - initial_ppo_weight) <= 0.0015 # allowing for some float precision/normalization slack

"""
Tests for the DynamicEnsemble weighting logic.
"""
import pytest
from src.models.dynamic_ensemble import DynamicWeightAdapter, MarketContext, ModelPerformance

def test_initial_weights():
    """Ensure weights are initialized correctly (equal by default)."""
    model_names = ["ppo", "lstm", "dreamer"]
    adapter = DynamicWeightAdapter(model_names)
    weights = adapter.get_weights()

    assert len(weights) == 3
    for name in model_names:
        assert weights[name] == pytest.approx(1/3)

def test_initial_weights_custom():
    """Ensure custom initial weights are respected and normalized."""
    model_names = ["ppo", "lstm"]
    initial = {"ppo": 0.8, "lstm": 0.2}
    adapter = DynamicWeightAdapter(model_names, initial_weights=initial)
    weights = adapter.get_weights()

    assert weights["ppo"] == pytest.approx(0.8)
    assert weights["lstm"] == pytest.approx(0.2)

def test_weight_update_performance():
    """Test that weights adapt to model performance."""
    model_names = ["ppo", "lstm"]
    # Fast adaptation for testing
    adapter = DynamicWeightAdapter(model_names, decay_factor=0.0)

    market = MarketContext(regime="trending", volatility=1.0)

    # Model 'ppo' performs much better
    perf = {
        "ppo": ModelPerformance(accuracy=0.8, calibration_score=0.9),
        "lstm": ModelPerformance(accuracy=0.5, calibration_score=0.5)
    }

    new_weights = adapter.update_weights(perf, market)

    assert new_weights["ppo"] > new_weights["lstm"]

def test_stability_decay():
    """Test that weights change gradually due to decay_factor."""
    model_names = ["ppo", "lstm"]
    # Slow adaptation
    adapter = DynamicWeightAdapter(model_names, decay_factor=0.9, min_weight=0.0)

    market = MarketContext(regime="trending", volatility=1.0)
    perf = {
        "ppo": ModelPerformance(accuracy=1.0, calibration_score=1.0),
        "lstm": ModelPerformance(accuracy=0.0, calibration_score=0.0)
    }

    # Starting from 0.5/0.5
    new_weights = adapter.update_weights(perf, market)

    # target for ppo is ~1.0, but decay=0.9 means:
    # 0.9 * 0.5 + 0.1 * 1.0 = 0.45 + 0.1 = 0.55
    assert new_weights["ppo"] == pytest.approx(0.55)

def test_clipping_caps():
    """Test that abrupt weight changes are capped."""
    model_names = ["ppo", "lstm"]
    # Fast adaptation but strict cap
    adapter = DynamicWeightAdapter(model_names, decay_factor=0.0, max_weight_change=0.05)

    market = MarketContext(regime="trending", volatility=1.0)
    perf = {
        "ppo": ModelPerformance(accuracy=1.0, calibration_score=1.0),
        "lstm": ModelPerformance(accuracy=0.0, calibration_score=0.0)
    }

    # Starting from 0.5/0.5, target is 1.0/0.0
    # Update would be 1.0, but capped at 0.5 + 0.05 = 0.55
    new_weights = adapter.update_weights(perf, market)

    assert new_weights["ppo"] == pytest.approx(0.55)

def test_min_weight_threshold():
    """Test that minimum weight is always respected."""
    model_names = ["ppo", "lstm"]
    adapter = DynamicWeightAdapter(model_names, min_weight=0.2, decay_factor=0.0)

    market = MarketContext(regime="trending", volatility=1.0)
    perf = {
        "ppo": ModelPerformance(accuracy=1.0, calibration_score=1.0),
        "lstm": ModelPerformance(accuracy=0.0, calibration_score=0.0)
    }

    new_weights = adapter.update_weights(perf, market)

    assert new_weights["lstm"] >= 0.2
    assert new_weights["ppo"] <= 0.8

def test_market_context_influence():
    """Test that market context (volatility) influences weighting logic."""
    model_names = ["ppo", "lstm"]
    adapter = DynamicWeightAdapter(model_names, decay_factor=0.0)

    # ppo: high accuracy, low calibration
    # lstm: medium accuracy, high calibration
    perf = {
        "ppo": ModelPerformance(accuracy=0.9, calibration_score=0.4),
        "lstm": ModelPerformance(accuracy=0.6, calibration_score=0.9)
    }

    # Low volatility: Accuracy might dominate
    market_low_vol = MarketContext(regime="ranging", volatility=1.0)
    weights_low = adapter.update_weights(perf, market_low_vol)

    # High volatility: Calibration is penalized/weighted more
    market_high_vol = MarketContext(regime="ranging", volatility=5.0)
    weights_high = adapter.update_weights(perf, market_high_vol)

    # In high vol, the well-calibrated model (lstm) should have more relative weight than in low vol
    # ppo_score_low = 0.9 * 0.4 = 0.36
    # lstm_score_low = 0.6 * 0.9 = 0.54
    # ratio_low = 0.36 / 0.54 = 0.66

    # ppo_score_high = 0.9 * 0.4 * 0.4 = 0.144
    # lstm_score_high = 0.6 * 0.9 * 0.9 = 0.486
    # ratio_high = 0.144 / 0.486 = 0.296

    assert weights_high["lstm"] > weights_low["lstm"]

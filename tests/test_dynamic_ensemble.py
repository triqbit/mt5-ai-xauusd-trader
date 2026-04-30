"""
Tests for DynamicEnsemble weighting logic.
"""
import pytest
import numpy as np
from src.models.dynamic_ensemble import DynamicEnsemble

def test_initialization():
    model_names = ["ppo", "lstm", "dreamer"]
    ensemble = DynamicEnsemble(model_names)
    weights = ensemble.get_weights()

    assert len(weights) == 3
    assert pytest.approx(sum(weights.values())) == 1.0
    for name in model_names:
        assert weights[name] == pytest.approx(1/3)

def test_update_metrics_and_step():
    model_names = ["m1", "m2"]
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=1.0)

    # m1 performs better
    ensemble.update_metrics("m1", accuracy=0.8, calibration_error=0.05)
    ensemble.update_metrics("m2", accuracy=0.4, calibration_error=0.2)

    weights = ensemble.step()

    assert weights["m1"] > 0.5
    assert weights["m2"] < 0.5
    assert pytest.approx(sum(weights.values())) == 1.0

def test_ema_smoothing():
    model_names = ["m1", "m2"]
    # Low alpha means slow adaptation
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=0.1)

    ensemble.update_metrics("m1", accuracy=0.9)
    ensemble.update_metrics("m2", accuracy=0.1)

    weights = ensemble.step()

    # Target for m1 would be high, but EMA should slow it down
    # Raw scores: m1=0.9, m2=0.1 -> targets: m1=0.9, m2=0.1
    # EMA: 0.9 * 0.5 + 0.1 * 0.9 = 0.45 + 0.09 = 0.54
    assert weights["m1"] == pytest.approx(0.54)

def test_max_weight_change_cap():
    model_names = ["m1", "m2"]
    # High alpha, but tight cap
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=1.0, max_weight_change=0.02)

    ensemble.update_metrics("m1", accuracy=0.9)
    ensemble.update_metrics("m2", accuracy=0.1)

    weights = ensemble.step()

    # Change is capped at 0.02
    assert weights["m1"] == pytest.approx(0.52)
    assert weights["m2"] == pytest.approx(0.48)

def test_min_weight_floor():
    model_names = ["m1", "m2"]
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=1.0, min_weight=0.1)

    # m2 performs extremely poorly
    ensemble.update_metrics("m1", accuracy=1.0)
    ensemble.update_metrics("m2", accuracy=0.0)

    weights = ensemble.step()

    assert weights["m2"] >= 0.1
    assert pytest.approx(sum(weights.values())) == 1.0

def test_regime_bias_volatile():
    model_names = ["m1", "m2"]
    # Large max_weight_change to reach target quickly for testing
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=1.0, max_weight_change=1.0)

    ensemble.update_metrics("m1", accuracy=0.9)
    ensemble.update_metrics("m2", accuracy=0.1)

    # Normal regime
    weights_normal = ensemble.step()

    # Volatile regime should flatten weights
    ensemble.update_context(regime="volatile")
    weights_volatile = ensemble.step()

    # In volatile regime, m1 should have less weight than in normal regime given same performance
    assert weights_volatile["m1"] < weights_normal["m1"]
    assert weights_volatile["m2"] > weights_normal["m2"]

def test_oscillation_dampening():
    model_names = ["m1", "m2"]
    # ema_alpha=1.0 to see immediate effect of dampened targets
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=1.0, max_weight_change=1.0)

    # 1. First step: Target m1 higher
    ensemble.update_metrics("m1", accuracy=0.8)
    ensemble.update_metrics("m2", accuracy=0.2)
    weights1 = ensemble.step()
    # Scores: 0.8, 0.2 -> Targets: 0.8, 0.2
    # Prev targets set to 0.8, 0.2
    assert weights1["m1"] == pytest.approx(0.8)

    # 2. Second step: Target m1 much lower (oscillation)
    ensemble.update_metrics("m1", accuracy=0.1)
    ensemble.update_metrics("m2", accuracy=0.9)
    weights2 = ensemble.step()
    # Scores: 0.1, 0.9 -> Targets: 0.1, 0.9
    # Current weight m1 = 0.8. New target = 0.1. Previous target = 0.8.
    # Direction is DOWN. Previous target was effectively 0.8 (which was UP from 0.5).
    # Wait, the logic is: (target < current_weight and prev_target > current_weight)
    # At step 2: target=0.1, current=0.8. prev_target was 0.8.
    # prev_target is NOT > current_weight (it is equal).

    # Let's force a real oscillation.
    # Step 1: Weight 0.5 -> 0.8 (Target 0.8)
    # Step 2: Weight 0.8 -> 0.4 (Target 0.4, no dampening because 0.8 was prev target)
    # Step 3: Weight 0.4 -> 0.7 (Target 0.7, Dampening!)

    ensemble.update_metrics("m1", accuracy=0.4)
    ensemble.update_metrics("m2", accuracy=0.6)
    weights2 = ensemble.step()
    assert weights2["m1"] == pytest.approx(0.4)

    # Step 3: Target m1=0.7 (UP), while previous target was 0.4 (DOWN from 0.8)
    ensemble.update_metrics("m1", accuracy=0.7)
    ensemble.update_metrics("m2", accuracy=0.3)
    weights3 = ensemble.step()

    # Raw target was 0.7. Current was 0.4. Prev target was 0.4.
    # (0.7 > 0.4 and 0.4 < 0.4) is False.
    # Ah, the logic uses (prev_target < current_weight).

    # If Step 2 target was 0.2, and it reached 0.4 because of EMA/Cap:
    # Step 1: current=0.5, target=0.8. weights=0.8. prev_target=0.8.
    # Step 2: current=0.8, target=0.2. weights=0.2. prev_target=0.2.
    # Step 3: current=0.2, target=0.6. weights should be dampened.
    # current=0.2, target=0.6, prev_target=0.2. (0.6 > 0.2 and 0.2 < 0.2) STILL FALSE.

    # The issue is when target moves PAST current weight in opposite direction of where it was heading.
    # If it's returning to the same spot as prev_target, it might not be an oscillation?
    # Oscillation is: UP then DOWN then UP.

    # Let's use EMA to keep current_weight away from target.
    ensemble = DynamicEnsemble(model_names, initial_weights={"m1": 0.5, "m2": 0.5}, ema_alpha=0.5, max_weight_change=1.0)

    # Step 1: target=0.9. current=0.5. weights = 0.5*0.5 + 0.5*0.9 = 0.7. prev_target=0.9.
    ensemble.update_metrics("m1", accuracy=0.9)
    ensemble.update_metrics("m2", accuracy=0.1)
    weights1 = ensemble.step()
    assert weights1["m1"] == 0.7

    # Step 2: target=0.1. current=0.7. prev_target=0.9.
    # (target < current and prev_target > current) -> (0.1 < 0.7 and 0.9 > 0.7) is TRUE!
    # Dampened target = 0.5 * (0.1 + 0.7) = 0.4.
    # New weight = 0.5 * 0.7 + 0.5 * 0.4 = 0.35 + 0.2 = 0.55.
    ensemble.update_metrics("m1", accuracy=0.1)
    ensemble.update_metrics("m2", accuracy=0.9)
    weights2 = ensemble.step()
    assert weights2["m1"] == pytest.approx(0.55)

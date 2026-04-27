"""
Tests for the DynamicEnsemble module.
"""

import pytest
from src.models.dynamic_ensemble import DynamicEnsemble, MarketRegime


def test_initialization():
    model_names = ["model_a", "model_b"]
    ensemble = DynamicEnsemble(model_names)
    weights = ensemble.get_weights()
    assert weights["model_a"] == 0.5
    assert weights["model_b"] == 0.5


def test_update_weights_accuracy():
    model_names = ["model_a", "model_b"]
    ensemble = DynamicEnsemble(model_names, smoothing_factor=1.0) # Faster adaptation for testing

    accuracies = {"model_a": 0.8, "model_b": 0.4}
    calibrations = {"model_a": 1.0, "model_b": 1.0}
    drift_signals = {"model_a": 0.0, "model_b": 0.0}

    ensemble.update_weights(
        MarketRegime.RANGING,
        accuracies,
        calibrations,
        0.1,
        drift_signals
    )

    weights = ensemble.get_weights()
    # model_a should have a higher weight now
    assert weights["model_a"] > weights["model_b"]


def test_max_weight_change_cap():
    model_names = ["model_a", "model_b"]
    # Max change 0.05, smoothing 1.0, decay 0.0 to see immediate impact
    ensemble = DynamicEnsemble(
        model_names,
        max_weight_change=0.05,
        smoothing_factor=1.0,
        decay_rate=0.0
    )

    # Drastic accuracy difference
    accuracies = {"model_a": 0.9, "model_b": 0.1}
    calibrations = {"model_a": 1.0, "model_b": 1.0}
    drift_signals = {"model_a": 0.0, "model_b": 0.0}

    ensemble.update_weights(
        MarketRegime.RANGING,
        accuracies,
        calibrations,
        0.1,
        drift_signals
    )

    weights = ensemble.get_weights()
    # Initial was 0.5. Max change is 0.05, so model_a should be at most 0.55
    # (Actually it might be slightly different due to normalization, but close)
    assert weights["model_a"] <= 0.551
    assert weights["model_a"] >= 0.549


def test_drift_penalty():
    model_names = ["model_a", "model_b"]
    ensemble = DynamicEnsemble(model_names, smoothing_factor=1.0)

    accuracies = {"model_a": 0.6, "model_b": 0.6}
    calibrations = {"model_a": 1.0, "model_b": 1.0}
    # model_b has drift
    drift_signals = {"model_a": 0.0, "model_b": 0.5}

    ensemble.update_weights(
        MarketRegime.RANGING,
        accuracies,
        calibrations,
        0.1,
        drift_signals
    )

    weights = ensemble.get_weights()
    assert weights["model_a"] > weights["model_b"]


def test_min_weight_floor():
    model_names = ["model_a", "model_b"]
    ensemble = DynamicEnsemble(model_names, min_weight=0.1, smoothing_factor=1.0)

    # model_b is terrible
    accuracies = {"model_a": 1.0, "model_b": 0.0}
    calibrations = {"model_a": 1.0, "model_b": 1.0}
    drift_signals = {"model_a": 0.0, "model_b": 0.0}

    # Multiple updates to push it to the floor
    for _ in range(10):
        ensemble.update_weights(
            MarketRegime.RANGING,
            accuracies,
            calibrations,
            0.1,
            drift_signals
        )

    weights = ensemble.get_weights()
    assert weights["model_b"] >= 0.1


def test_stability_smoothing():
    model_names = ["model_a", "model_b"]
    # Low smoothing factor for stability
    ensemble = DynamicEnsemble(model_names, smoothing_factor=0.1)

    accuracies = {"model_a": 0.9, "model_b": 0.1}
    calibrations = {"model_a": 1.0, "model_b": 1.0}
    drift_signals = {"model_a": 0.0, "model_b": 0.0}

    initial_w_a = ensemble.weights["model_a"]

    ensemble.update_weights(
        MarketRegime.RANGING,
        accuracies,
        calibrations,
        0.1,
        drift_signals
    )

    weights = ensemble.get_weights()
    # Change should be small due to smoothing
    change = weights["model_a"] - initial_w_a
    assert change < 0.05

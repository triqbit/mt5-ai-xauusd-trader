"""
Tests for walk-forward optimization logic.
"""

import pytest
import numpy as np
from src.research.hyperopt_walkforward import (
    WalkForwardOptimizer, WalkForwardConfig, HyperparameterSet, Evaluator
)

class MockEvaluator:
    def evaluate(self, params, start_idx, end_idx):
        # Simple mock: return a value based on a parameter and indices
        val = params.get("val", 1.0)
        # Simulate some variance across windows
        metric = val * (1.0 + 0.1 * np.sin(start_idx))
        return {"sharpe": metric}

def test_generate_windows_rolling():
    config = WalkForwardConfig(
        train_window_size=100,
        test_window_size=20,
        step_size=20,
        anchored=False
    )
    optimizer = WalkForwardOptimizer(config, data_length=200)
    windows = optimizer.generate_windows()

    assert len(windows) == 5
    assert windows[0].train_start == 0
    assert windows[0].train_end == 100
    assert windows[0].test_start == 100
    assert windows[0].test_end == 120

    assert windows[-1].test_end == 200
    assert windows[-1].train_start == 80

def test_generate_windows_anchored():
    config = WalkForwardConfig(
        train_window_size=100,
        test_window_size=20,
        step_size=20,
        anchored=True
    )
    optimizer = WalkForwardOptimizer(config, data_length=200)
    windows = optimizer.generate_windows()

    assert len(windows) == 5
    assert windows[0].train_start == 0
    assert windows[-1].train_start == 0
    assert windows[-1].train_end == 180

def test_robustness_score():
    config = WalkForwardConfig(train_window_size=10, test_window_size=5, step_size=5)
    optimizer = WalkForwardOptimizer(config, data_length=100)

    # Consistent positive returns
    score_high = optimizer.calculate_robustness_score([1.0, 1.1, 0.9, 1.0])
    # Volatile returns
    score_low = optimizer.calculate_robustness_score([2.0, 0.1, 1.5, -0.5])

    assert score_high > score_low

def test_parameter_stability():
    config = WalkForwardConfig(train_window_size=10, test_window_size=5, step_size=5)
    optimizer = WalkForwardOptimizer(config, data_length=100)

    params = [{"a": 10, "b": 1.0}, {"a": 11, "b": 1.1}, {"a": 9, "b": 0.9}]
    stability = optimizer.analyze_parameter_stability(params)

    assert "a_cv" in stability
    assert "b_cv" in stability
    assert stability["a_cv"] > 0

def test_run_walk_forward():
    config = WalkForwardConfig(
        train_window_size=50,
        test_window_size=10,
        step_size=10,
        anchored=False
    )
    optimizer = WalkForwardOptimizer(config, data_length=100)
    evaluator = MockEvaluator()
    candidates = [
        HyperparameterSet(params={"val": 1.0}, id="set1"),
        HyperparameterSet(params={"val": 2.0}, id="set2")
    ]

    summary = optimizer.run_walk_forward(evaluator, candidates)

    assert len(summary.window_results) > 0
    assert summary.robustness_score >= 0
    assert summary.avg_oos_performance != 0

def test_rank_candidates():
    config = WalkForwardConfig(
        train_window_size=50,
        test_window_size=10,
        step_size=10,
        anchored=False
    )
    optimizer = WalkForwardOptimizer(config, data_length=100)
    evaluator = MockEvaluator()
    candidates = [
        HyperparameterSet(params={"val": 1.0}, id="set1"),
        HyperparameterSet(params={"val": 0.1}, id="set2") # intentionally worse
    ]

    ranked = optimizer.rank_candidates(evaluator, candidates)
    assert ranked[0][0].params["val"] == 1.0

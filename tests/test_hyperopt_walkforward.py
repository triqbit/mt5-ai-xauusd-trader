"""
Tests for Walk-Forward Optimization.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.benchmarks import EMACrossoverStrategy
from src.research.hyperopt_walkforward import WalkForwardConfig, WalkForwardOptimizer


@pytest.fixture
def sample_data():
    np.random.seed(42)
    n = 500
    df = pd.DataFrame(
        {
            "open": np.random.randn(n) + 2000,
            "high": np.random.randn(n) + 2005,
            "low": np.random.randn(n) + 1995,
            "close": np.random.randn(n) + 2000,
            "tick_volume": np.random.randint(100, 1000, n),
        }
    )
    return df


def test_window_generation(sample_data):
    config = WalkForwardConfig(train_size=100, test_size=20, step_size=20)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=lambda t: {},
        config=config,
    )

    windows = optimizer.generate_windows()
    # 500 total. 100 train + 20 test = 120.
    # Start at 0, 20, 40, ...
    # Last start: 500 - 120 = 380.
    # Starts: 0, 20, 40, ..., 380.
    # Number of steps = (380 - 0) / 20 + 1 = 20.
    assert len(windows) == 20

    train, test = windows[0]
    assert len(train) == 100
    assert len(test) == 20
    assert train.index[-1] < test.index[0]


def test_robustness_scoring_components(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 10),
            "slow_window": trial.suggest_int("slow_window", 20, 30),
        }

    config = WalkForwardConfig(n_trials=2, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
    )

    params = {"fast_window": 9, "slow_window": 21}

    # Test stability penalty
    stability = optimizer._calculate_stability_penalty(params, sample_data)
    assert isinstance(stability, float)

    # Test regime consistency
    consistency = optimizer._calculate_regime_consistency(optimizer.data, params)
    assert 0 <= consistency <= 1.0


def test_full_optimization_run(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 15),
            "slow_window": trial.suggest_int("slow_window", 20, 40),
        }

    config = WalkForwardConfig(
        n_trials=5, train_size=200, test_size=50, step_size=50, min_windows=3
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
    )

    result = optimizer.run_optimization()

    assert "fast_window" in result.best_params
    assert "slow_window" in result.best_params
    assert result.metrics.robustness_score is not None
    assert result.metrics.oos_sharpe_mean is not None

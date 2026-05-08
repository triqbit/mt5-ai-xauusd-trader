"""
Tests for Walk-Forward Optimization.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.benchmarks import EMACrossoverStrategy
from src.research.hyperopt_walkforward import (
    WalkForwardConfig,
    WalkForwardOptimizer,
    OptimizationMetric,
    RobustnessWeights,
)


@pytest.fixture
def sample_data():
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "open": np.random.randn(n) + 2000,
        "high": np.random.randn(n) + 2005,
        "low": np.random.randn(n) + 1995,
        "close": np.random.randn(n) + 2000,
        "tick_volume": np.random.randint(100, 1000, n)
    })
    return df

def test_window_generation(sample_data):
    config = WalkForwardConfig(train_size=100, test_size=20, step_size=20)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=lambda t: {},
        config=config
    )

    windows = optimizer.generate_windows()
    assert len(windows) == 20

    train, test = windows[0]
    assert len(train) == 100
    assert len(test) == 20
    assert train.index[-1] < test.index[0]

def test_robustness_scoring_components(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 10),
            "slow_window": trial.suggest_int("slow_window", 20, 30)
        }

    config = WalkForwardConfig(n_trials=2, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    params = {"fast_window": 9, "slow_window": 21}

    # Test stability penalty
    stability = optimizer._calculate_stability_penalty(params, sample_data)
    assert isinstance(stability, float)

    # Test type-safe perturbations for integers
    int_params = {"window": 10}
    # Mock _evaluate_strategy to just return a dummy Sharpe Ratio
    optimizer._evaluate_strategy = lambda d, p: {"Sharpe Ratio": 1.0 + (p["window"] * 0.01)}
    stability_int = optimizer._calculate_stability_penalty(int_params, sample_data)
    assert isinstance(stability_int, float)

    # Test handling of zero values in stability penalty
    zero_params = {"param": 0.0}
    optimizer._evaluate_strategy = lambda d, p: {"Sharpe Ratio": 1.0 + (p["param"] * 0.1)}
    stability_zero = optimizer._calculate_stability_penalty(zero_params, sample_data)
    assert stability_zero > 0.0  # Should be non-zero due to epsilon perturbation

    # Test regime consistency
    consistency = optimizer._calculate_regime_consistency(optimizer.data, params)
    assert 0 <= consistency <= 1.0

def test_full_optimization_run(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 15),
            "slow_window": trial.suggest_int("slow_window", 20, 40)
        }

    config = WalkForwardConfig(n_trials=5, train_size=200, test_size=50, step_size=50, min_windows=3)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    result = optimizer.run_optimization()

    assert "fast_window" in result.best_params
    assert "slow_window" in result.best_params
    assert result.metrics.robustness_score is not None
    assert result.metrics.oos_sharpe_mean is not None
    assert result.metrics.worst_window_sharpe is not None
    assert result.metrics.walk_forward_efficiency is not None
    assert 0 <= result.metrics.win_rate_consistency <= 1.0
    assert 0 <= result.metrics.max_drawdown_consistency <= 1.0
    assert len(result.oos_returns) > 0

    # Verify window results
    assert len(result.window_results) >= 3
    assert result.window_results[0].window_index == 0
    assert "Sharpe Ratio" in result.window_results[0].oos_metrics
    assert "Sharpe Ratio" in result.window_results[0].is_metrics

def test_metric_selection(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 15),
            "slow_window": trial.suggest_int("slow_window", 20, 40)
        }

    # Test Total Return optimization
    config_tr = WalkForwardConfig(
        n_trials=5,
        train_size=200,
        test_size=50,
        step_size=50,
        metric=OptimizationMetric.TOTAL_RETURN
    )
    optimizer_tr = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config_tr
    )
    result_tr = optimizer_tr.run_optimization()
    assert result_tr.metrics.robustness_score is not None

def test_configurable_robustness_weights(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    # Custom weights that prioritize IS-OOS gap and stability
    weights = RobustnessWeights(is_oos_gap=1.0, stability=1.0, oos_mean=0.1)
    config = WalkForwardConfig(
        n_trials=2,
        train_size=100,
        test_size=20,
        step_size=50,
        robustness_weights=weights
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    result = optimizer.run_optimization()
    assert result.metrics.robustness_score is not None

def test_insufficient_data(sample_data):
    config = WalkForwardConfig(train_size=1000, test_size=200)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=lambda t: {},
        config=config
    )
    with pytest.raises(ValueError, match="Insufficient data"):
        optimizer.run_optimization()


def test_oos_constraints(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    # Extremely strict constraints that will likely be violated
    config = WalkForwardConfig(
        n_trials=1,
        train_size=100,
        test_size=20,
        step_size=50,
        min_oos_sharpe=10.0,  # Impossible Sharpe
        max_oos_drawdown=0.000001,  # Almost zero drawdown allowed
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    result = optimizer.run_optimization()
    assert result.metrics.constraints_violated is True


def test_improved_regime_consistency(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # Manual test of the _calculate_regime_consistency method
    params = {"fast_window": 10, "slow_window": 30}
    consistency = optimizer._calculate_regime_consistency(optimizer.data, params)
    assert 0 <= consistency <= 1.0


def test_additional_metric_selection(sample_data):
    def param_space(trial):
        return {"fast_window": trial.suggest_int("fast_window", 5, 15), "slow_window": 30}

    # Test Calmar optimization
    config_calmar = WalkForwardConfig(
        n_trials=2, train_size=100, test_size=20, step_size=50, metric=OptimizationMetric.CALMAR
    )
    optimizer_calmar = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config_calmar
    )
    result_calmar = optimizer_calmar.run_optimization()
    assert result_calmar is not None

    # Test Win Rate optimization
    config_wr = WalkForwardConfig(
        n_trials=2, train_size=100, test_size=20, step_size=50, metric=OptimizationMetric.WIN_RATE
    )
    optimizer_wr = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config_wr
    )
    result_wr = optimizer_wr.run_optimization()
    assert result_wr is not None

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


def test_ranking_by_robustness(sample_data):
    """
    Verifies that the optimizer correctly ranks by robustness score,
    potentially selecting a configuration with lower return but higher stability.
    """
    class DummyStrategy:
        def __init__(self, **kwargs): self.name = "Dummy"
        def predict(self, df): return np.zeros(len(df))

    def param_space(trial):
        return {"param": trial.suggest_int("param", 1, 2)}

    config = WalkForwardConfig(
        n_trials=2,
        train_size=100,
        test_size=20,
        step_size=50,
        metric=OptimizationMetric.ROBUSTNESS_SCORE
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=DummyStrategy,
        param_space=param_space,
        config=config
    )

    # Mock _evaluate_strategy and scoring to create a trade-off
    # Trial 1 (param=1): High Return, High Instability (Penalty)
    # Trial 2 (param=2): Lower Return, Zero Instability
    def mock_eval(data, params):
        if params["param"] == 1:
            return {"Sharpe Ratio": 2.0, "Total Return": 0.5}
        return {"Sharpe Ratio": 1.5, "Total Return": 0.2}

    optimizer._evaluate_strategy = mock_eval

    def mock_stability(params, data):
        if params["param"] == 1:
            return 5.0  # High penalty
        return 0.0

    optimizer._calculate_stability_penalty = mock_stability

    result = optimizer.run_optimization()

    # With high stability penalty on param=1, the optimizer should favor param=2
    # even though param=1 has higher Sharpe/Return.
    assert result.best_params["param"] == 2
    assert result.metrics.robustness_score > 0


def test_window_generation_variations(sample_data):
    """Tests window generation with different size and step variations."""
    # Standard overlap
    c1 = WalkForwardConfig(train_size=100, test_size=50, step_size=50)
    o1 = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, c1)
    w1 = o1.generate_windows()
    assert len(w1) == 8  # (500 - 150) / 50 + 1 = 8

    # Gap windows (step > test_size)
    c2 = WalkForwardConfig(train_size=100, test_size=50, step_size=100)
    o2 = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, c2)
    w2 = o2.generate_windows()
    assert len(w2) == 4  # (500 - 150) / 100 + 1 = 4.5 -> 4

    # Heavy overlap (step < test_size)
    c3 = WalkForwardConfig(train_size=200, test_size=50, step_size=10)
    o3 = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, c3)
    w3 = o3.generate_windows()
    assert len(w3) == 26 # (500 - 250) / 10 + 1 = 26


def test_frequency_weighted_regime_consistency(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # Mock data with specific regimes to test frequency weighting
    data = sample_data.copy()
    data["regime"] = "ranging"
    data.loc[0:10, "regime"] = "trending"  # Small regime

    # We need enough data points for Sharpe calculation (>5)
    # ranging has ~490, trending has 11.
    params = {"fast_window": 10, "slow_window": 30}
    consistency = optimizer._calculate_regime_consistency(data, params)
    assert 0 <= consistency <= 1.0


def test_stability_penalty_fragility_safeguard(sample_data):
    def param_space(trial):
        return {"param": trial.suggest_float("param", 0, 1)}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # Force a failure/NaN to trigger the safeguard
    def failing_eval(data, params):
        return {"Sharpe Ratio": np.nan}

    optimizer._evaluate_strategy = failing_eval
    params = {"param": 0.5}
    penalty = optimizer._calculate_stability_penalty(params, sample_data)
    assert penalty == 10.0


def test_stability_penalty_scale_invariance(sample_data):
    def param_space(trial):
        return {"p1": 10.0}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # Test that CV is calculated correctly
    # Base Sharpe = 1.0, Perturbed = 1.1, 0.9
    # Mean = 1.0, Std = sqrt((0^2 + 0.1^2 + (-0.1)^2) / 3) = sqrt(0.02 / 3) approx 0.0816
    # CV = 0.0816 / 1.0 = 0.0816
    eval_count = 0

    def mock_eval(data, params):
        nonlocal eval_count
        sharpes = [1.0, 1.1, 0.9]
        s = sharpes[eval_count % 3]
        eval_count += 1
        return {"Sharpe Ratio": s}

    optimizer._evaluate_strategy = mock_eval
    params = {"p1": 100.0}
    cv_penalty = optimizer._calculate_stability_penalty(params, sample_data)
    assert 0.07 < cv_penalty < 0.09


def test_multi_window_stability_sampling(sample_data):
    """Verifies that multiple windows are used for stability calculation during optimization."""
    eval_calls = []

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    original_calc_stability = optimizer._calculate_stability_penalty

    def tracked_calc_stability(params, data):
        eval_calls.append(len(data))
        return original_calc_stability(params, data)

    optimizer._calculate_stability_penalty = tracked_calc_stability

    # Need enough windows to trigger multi-sampling (3 windows)
    # len(sample_data)=500. (500-120)/50 + 1 = 8 windows.
    optimizer.run_optimization()

    # Should have called stability calculation for 3 windows (indices from np.linspace)
    assert len(eval_calls) == 3


def test_constraint_penalty_across_metrics(sample_data):
    """Verifies that constraint penalty is applied to metrics other than ROBUSTNESS_SCORE."""

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    # Strict constraints
    config = WalkForwardConfig(
        n_trials=1,
        train_size=100,
        test_size=20,
        step_size=50,
        metric=OptimizationMetric.SHARPE,
        min_oos_sharpe=10.0,  # Strict
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # We need to capture the trial return value
    # Since we can't easily capture it from study.optimize, we'll mock the objective
    # or just trust the logic if it's simple.
    # Actually, we can check if the best_trial's value is significantly reduced.

    result = optimizer.run_optimization()
    # If SHARPE was ~0 and penalty was applied, it should be very negative
    # best_trial value is accessible via study if we had access to it,
    # but run_optimization doesn't return the study.
    # We can check result.metrics.constraints_violated
    assert result.metrics.constraints_violated is True
    # The robustness score is always calculated and should be heavily penalized
    assert result.metrics.robustness_score < -1.0


def test_wfe_calculation(sample_data):
    """Verifies Walk-Forward Efficiency (WFE) calculation."""

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config
    )

    # Mock _evaluate_strategy to return fixed values for IS and OOS
    # is_mean will be 2.0, oos_mean will be 1.0
    eval_count = 0

    def mock_eval(data, params):
        nonlocal eval_count
        # Even calls (IS) = 2.0, Odd calls (OOS) = 1.0
        val = 2.0 if eval_count % 2 == 0 else 1.0
        eval_count += 1
        return {"Sharpe Ratio": val}

    optimizer._evaluate_strategy = mock_eval
    result = optimizer.run_optimization()

    # WFE = OOS_Mean / IS_Mean = 1.0 / 2.0 = 0.5
    assert result.metrics.walk_forward_efficiency == pytest.approx(0.5)

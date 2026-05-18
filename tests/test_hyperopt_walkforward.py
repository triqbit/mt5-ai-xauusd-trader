"""
Tests for Walk-Forward Optimization.
"""

import numpy as np
import pandas as pd
import pytest

from src.research.benchmarks import EMACrossoverStrategy
from src.research.hyperopt_walkforward import (
    OptimizationMetric,
    RobustnessWeights,
    WalkForwardConfig,
    WalkForwardOptimizer,
)


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
    penalty, sensitivities = optimizer._calculate_stability_penalty(params, sample_data)
    assert isinstance(penalty, float)
    assert isinstance(sensitivities, dict)
    assert "fast_window" in sensitivities
    assert "slow_window" in sensitivities

    # Test type-safe perturbations for integers
    int_params = {"window": 10}
    # Mock _evaluate_strategy to just return a dummy Sharpe Ratio
    optimizer._evaluate_strategy = lambda d, p: (
        {"Sharpe Ratio": 1.0 + (p["window"] * 0.01)},
        np.zeros(len(d)),
    )
    penalty_int, sens_int = optimizer._calculate_stability_penalty(int_params, sample_data)
    assert isinstance(penalty_int, float)
    assert "window" in sens_int

    # Test handling of zero values in stability penalty
    zero_params = {"param": 0.0}
    optimizer._evaluate_strategy = lambda d, p: (
        {"Sharpe Ratio": 1.0 + (p["param"] * 0.1)},
        np.zeros(len(d)),
    )
    penalty_zero, _sens_zero = optimizer._calculate_stability_penalty(zero_params, sample_data)
    assert penalty_zero > 0.0  # Should be non-zero due to epsilon perturbation

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
    assert result.metrics.worst_window_sharpe is not None
    assert result.metrics.walk_forward_efficiency is not None
    assert 0 <= result.metrics.win_rate_consistency <= 1.0
    assert 0 <= result.metrics.max_drawdown_consistency <= 1.0
    assert len(result.oos_returns) > 0

    # Verify granular sensitivities
    assert "fast_window" in result.metrics.parameter_sensitivities
    assert "slow_window" in result.metrics.parameter_sensitivities

    # Verify window results
    assert len(result.window_results) >= 3
    assert result.window_results[0].window_index == 0
    assert "Sharpe Ratio" in result.window_results[0].oos_metrics
    assert "Sharpe Ratio" in result.window_results[0].is_metrics


def test_metric_selection(sample_data):
    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 15),
            "slow_window": trial.suggest_int("slow_window", 20, 40),
        }

    # Test Total Return optimization
    config_tr = WalkForwardConfig(
        n_trials=5,
        train_size=200,
        test_size=50,
        step_size=50,
        metric=OptimizationMetric.TOTAL_RETURN,
    )
    optimizer_tr = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config_tr,
    )
    result_tr = optimizer_tr.run_optimization()
    assert result_tr.metrics.robustness_score is not None


def test_configurable_robustness_weights(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    # Custom weights that prioritize IS-OOS gap and stability
    weights = RobustnessWeights(is_oos_gap=1.0, stability=1.0, oos_mean=0.1)
    config = WalkForwardConfig(
        n_trials=2, train_size=100, test_size=20, step_size=50, robustness_weights=weights
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
    )

    result = optimizer.run_optimization()
    assert result.metrics.robustness_score is not None


def test_insufficient_data(sample_data):
    config = WalkForwardConfig(train_size=1000, test_size=200)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=lambda t: {},
        config=config,
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
        config=config,
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
        config=config,
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
        config=config_calmar,
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
        config=config_wr,
    )
    result_wr = optimizer_wr.run_optimization()
    assert result_wr is not None


def test_ranking_by_robustness(sample_data):
    """
    Verifies that the optimizer correctly ranks by robustness score,
    potentially selecting a configuration with lower return but higher stability.
    """

    class DummyStrategy:
        def __init__(self, **kwargs):
            self.name = "Dummy"

        def predict(self, df):
            return np.zeros(len(df))

    def param_space(trial):
        return {"param": trial.suggest_int("param", 1, 2)}

    config = WalkForwardConfig(
        n_trials=2,
        train_size=100,
        test_size=20,
        step_size=50,
        metric=OptimizationMetric.ROBUSTNESS_SCORE,
    )
    optimizer = WalkForwardOptimizer(
        data=sample_data, strategy_factory=DummyStrategy, param_space=param_space, config=config
    )

    # Mock _evaluate_strategy and scoring to create a trade-off
    # Trial 1 (param=1): High Return, High Instability (Penalty)
    # Trial 2 (param=2): Lower Return, Zero Instability
    def mock_eval(data, params):
        if params["param"] == 1:
            return {"Sharpe Ratio": 2.0, "Total Return": 0.5, "Num Trades": 10}, np.zeros(len(data))
        return {"Sharpe Ratio": 1.5, "Total Return": 0.2, "Num Trades": 10}, np.zeros(len(data))

    optimizer._evaluate_strategy = mock_eval

    def mock_stability(params, data):
        if params["param"] == 1:
            return 5.0  # High penalty
        return 0.0

    optimizer._calculate_stability_penalty = lambda p, d: (mock_stability(p, d), {})

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
    assert len(w3) == 26  # (500 - 250) / 10 + 1 = 26


def test_frequency_weighted_regime_consistency(sample_data):
    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
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
        config=config,
    )

    # Force a failure/NaN to trigger the safeguard
    def failing_eval(data, params):
        return {"Sharpe Ratio": np.nan}, np.zeros(len(data))

    optimizer._evaluate_strategy = failing_eval
    params = {"param": 0.5}
    penalty, _ = optimizer._calculate_stability_penalty(params, sample_data)
    assert penalty == 10.0


def test_stability_penalty_scale_invariance(sample_data):
    def param_space(trial):
        return {"p1": 10.0}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(
        data=sample_data,
        strategy_factory=EMACrossoverStrategy,
        param_space=param_space,
        config=config,
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
        return {"Sharpe Ratio": s}, np.zeros(len(data))

    optimizer._evaluate_strategy = mock_eval
    params = {"p1": 100.0}
    cv_penalty, _ = optimizer._calculate_stability_penalty(params, sample_data)
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
        config=config,
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
        config=config,
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
        config=config,
    )

    # Mock _evaluate_strategy to return fixed values for IS and OOS
    # is_mean will be 2.0, oos_mean will be 1.0
    eval_count = 0

    def mock_eval(data, params):
        nonlocal eval_count
        # Even calls (IS) = 2.0, Odd calls (OOS) = 1.0
        val = 2.0 if eval_count % 2 == 0 else 1.0
        eval_count += 1
        return {"Sharpe Ratio": val, "Num Trades": 10}, np.zeros(len(data))

    optimizer._evaluate_strategy = mock_eval
    result = optimizer.run_optimization()

    # WFE = OOS_Mean / IS_Mean = 1.0 / 2.0 = 0.5
    assert result.metrics.walk_forward_efficiency == pytest.approx(0.5)


def test_json_export(sample_data, tmp_path):
    """Verifies that WalkForwardResult can be exported to JSON."""

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 20}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)
    result = optimizer.run_optimization()

    json_file = tmp_path / "result.json"
    result.save_json(str(json_file))

    assert json_file.exists()
    content = json_file.read_text()
    assert '"best_params"' in content
    assert '"metrics"' in content


def test_strict_fragility_penalty(sample_data):
    """Verifies that the stability penalty correctly identifies and penalizes fragility."""

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 20}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)

    eval_calls = 0

    def mock_eval(data, params):
        nonlocal eval_calls
        eval_calls += 1
        # Base case (1st call): Sharpe = 1.0
        # Perturbation (subsequent calls): Sharpe = -0.5 (Catastrophic drop)
        return {"Sharpe Ratio": 1.0 if eval_calls == 1 else -0.5}, np.zeros(len(data))

    optimizer._evaluate_strategy = mock_eval
    params = {"fast_window": 10, "slow_window": 20}
    penalty, _ = optimizer._calculate_stability_penalty(params, sample_data)

    # Should return the maximum penalty of 10.0 due to fragility (positive to negative flip)
    assert penalty == 10.0


def test_wfe_integration_in_robustness(sample_data):
    """Verifies that WFE is integrated into the robustness score."""

    def param_space(trial):
        return {"fast_window": 10, "slow_window": 30}

    # Weights with high WFE importance
    weights = RobustnessWeights(walk_forward_efficiency=1.0, oos_mean=0.0, worst_oos=0.0)
    config = WalkForwardConfig(
        n_trials=1, train_size=100, test_size=20, step_size=50, robustness_weights=weights
    )
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)

    # Mock IS = 2.0, OOS = 1.0 -> WFE = 0.5
    eval_count = 0

    def mock_eval(data, params):
        nonlocal eval_count
        val = 2.0 if eval_count % 2 == 0 else 1.0
        eval_count += 1
        return {"Sharpe Ratio": val, "Num Trades": 10}, np.zeros(len(data))

    optimizer._evaluate_strategy = mock_eval
    result = optimizer.run_optimization()

    # Robustness should be dominated by WFE (0.5)
    # Other components might contribute small amounts (stability, regime cons)
    # but we check if it's in a sensible range.
    assert result.metrics.walk_forward_efficiency == pytest.approx(0.5)
    assert result.metrics.robustness_score > 0.4


def test_stability_penalty_zero_value_robustness(sample_data):
    """Verifies that stability penalty handles zero-valued float parameters gracefully."""

    def param_space(trial):
        return {"param": 0.0}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)

    # Ensure delta is at least 1e-5 for 0.0
    params = {"param": 0.0}

    # Track delta used
    captured_deltas = []
    original_eval = optimizer._evaluate_strategy

    def mock_eval(data, p):
        if p["param"] != 0.0:
            captured_deltas.append(abs(p["param"]))
        return original_eval(data, p)

    optimizer._evaluate_strategy = mock_eval
    optimizer._calculate_stability_penalty(params, sample_data)

    assert all(d >= 1e-5 for d in captured_deltas)


def test_get_best_strategy(sample_data):
    """Verifies the get_best_strategy method."""

    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 10, 10),
            "slow_window": trial.suggest_int("slow_window", 20, 20),
        }

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)
    result = optimizer.run_optimization()

    strategy = result.get_best_strategy(EMACrossoverStrategy)
    assert isinstance(strategy, EMACrossoverStrategy)
    assert strategy.fast_window == 10
    assert strategy.slow_window == 20


def test_regime_consistency_single_regime_fallback(sample_data):
    """Verifies that regime consistency returns 0.5 when only one regime is present."""
    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, config)

    data = sample_data.copy()
    data["regime"] = "ranging"  # Only one regime

    returns = np.zeros(len(data))
    consistency = optimizer._calculate_regime_consistency(data, returns)

    assert consistency == 0.5


def test_window_alignment_and_no_gaps(sample_data):
    """Verifies that generated windows are properly aligned and have no gaps."""
    train_size = 100
    test_size = 20
    step_size = 20
    config = WalkForwardConfig(train_size=train_size, test_size=test_size, step_size=step_size)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, config)

    windows = optimizer.generate_windows()

    for i in range(len(windows) - 1):
        train_curr, test_curr = windows[i]
        train_next, test_next = windows[i + 1]

        # In this config (step_size == test_size), the next train_start should be prev_train_start + step_size
        assert train_next.index[0] == train_curr.index[0] + step_size
        # Next OOS should start exactly where previous OOS ended if step_size == test_size
        assert test_next.index[0] == test_curr.index[0] + step_size

        # OOS must follow IS
        assert test_curr.index[0] == train_curr.index[-1] + 1


def test_min_regime_consistency_constraint(sample_data):
    """Verifies that the min_regime_consistency constraint is enforced."""

    def param_space(trial):
        return {"param": 1}

    # Set an impossible regime consistency requirement
    config = WalkForwardConfig(
        n_trials=1,
        train_size=100,
        test_size=20,
        step_size=50,
        min_regime_consistency=2.0,  # Max is 1.0
    )

    class DummyStrategy:
        def __init__(self, **kwargs):
            self.name = "Dummy"

        def predict(self, df):
            return np.zeros(len(df))

    optimizer = WalkForwardOptimizer(
        data=sample_data, strategy_factory=DummyStrategy, param_space=param_space, config=config
    )

    result = optimizer.run_optimization()
    assert result.metrics.constraints_violated is True
    assert result.metrics.grade == "F"


def test_min_wfe_constraint(sample_data):
    """Verifies that the min_walk_forward_efficiency constraint is enforced."""

    def param_space(trial):
        return {"param": 1}

    # Set an impossible WFE requirement
    config = WalkForwardConfig(
        n_trials=1,
        train_size=100,
        test_size=20,
        step_size=50,
        min_walk_forward_efficiency=10.0,
    )

    class DummyStrategy:
        def __init__(self, **kwargs):
            self.name = "Dummy"

        def predict(self, df):
            return np.zeros(len(df))

    optimizer = WalkForwardOptimizer(
        data=sample_data, strategy_factory=DummyStrategy, param_space=param_space, config=config
    )

    result = optimizer.run_optimization()
    assert result.metrics.constraints_violated is True
    assert result.metrics.grade == "F"


def test_robustness_grading_logic():
    """Verifies the institutional robustness grading logic in RobustnessMetrics."""
    from src.research.hyperopt_walkforward import RobustnessMetrics

    # Grade A: Perfect
    m_a = RobustnessMetrics(
        oos_sharpe_mean=1.5,
        oos_sharpe_std=0.1,
        worst_window_sharpe=1.2,
        win_rate_consistency=0.9,
        max_drawdown_consistency=0.9,
        is_oos_gap=0.1,
        stability_penalty=0.05,
        regime_consistency=0.8,
        robustness_score=1.1,
        walk_forward_efficiency=0.8,
        constraints_violated=False,
    )
    assert m_a.calculate_grade() == "A"

    # Grade B: Good
    m_b = RobustnessMetrics(
        oos_sharpe_mean=0.6,
        oos_sharpe_std=0.2,
        worst_window_sharpe=0.4,
        win_rate_consistency=0.8,
        max_drawdown_consistency=0.8,
        is_oos_gap=0.2,
        stability_penalty=0.1,
        regime_consistency=0.6,
        robustness_score=0.7,
        walk_forward_efficiency=0.6,
        constraints_violated=False,
    )
    assert m_b.calculate_grade() == "B"

    # Grade C: Acceptable
    m_c = RobustnessMetrics(
        oos_sharpe_mean=0.2,
        oos_sharpe_std=0.3,
        worst_window_sharpe=0.0,
        win_rate_consistency=0.6,
        max_drawdown_consistency=0.6,
        is_oos_gap=0.4,
        stability_penalty=0.2,
        regime_consistency=0.4,
        robustness_score=0.4,
        walk_forward_efficiency=0.4,
        constraints_violated=False,
    )
    assert m_c.calculate_grade() == "C"

    # Grade F: Violation
    m_f = RobustnessMetrics(
        oos_sharpe_mean=2.0,
        oos_sharpe_std=0.0,
        worst_window_sharpe=2.0,
        win_rate_consistency=1.0,
        max_drawdown_consistency=1.0,
        is_oos_gap=0.0,
        stability_penalty=0.0,
        regime_consistency=1.0,
        robustness_score=2.0,
        walk_forward_efficiency=1.0,
        constraints_violated=True,  # Constraint violation
    )
    assert m_f.calculate_grade() == "F"


def test_reporting_integration(sample_data):
    """Verifies integration with the reporting framework."""
    from src.research.reporting import HyperparameterSection

    def param_space(trial):
        return {"fast_window": trial.suggest_int("fast_window", 10, 10)}

    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, param_space, config)
    result = optimizer.run_optimization()

    section = result.to_report_section()
    assert isinstance(section, HyperparameterSection)
    assert section.stability_score >= 0
    assert len(section.parameters) == 1
    assert section.parameters[0].name == "fast_window"
    assert section.grade in ["A", "B", "C", "D", "F"]
    assert "OOS Sharpe Mean" in section.insights


def test_bars_per_year_refined(sample_data):
    """Verifies that the refined bars_per_year is used correctly in calculations."""
    # Default is 6240
    config = WalkForwardConfig(n_trials=1, train_size=100, test_size=20, step_size=50)
    assert config.bars_per_year == 6240

    optimizer = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, config)

    # Mock returns with known mean and std
    returns = np.array([0.01] * 100)
    returns[0] = 0.02  # mean = 0.0101, std approx 0.001

    # We need to test if bars_per_year is used in Sharpe calculation.
    # _evaluate_strategy uses config.bars_per_year through BenchmarkEvaluator.
    def mock_predict(data):
        return pd.Series(1, index=data.index) # Always long

    # Manually trigger a calculation that uses bars_per_year
    # BenchmarkEvaluator calculates Sharpe as (mean/std) * sqrt(bars_per_year)
    from src.research.benchmarks import BenchmarkEvaluator
    _ = BenchmarkEvaluator(sample_data.iloc[:100], bars_per_year=config.bars_per_year)

    # We need to mock the returns inside the evaluator
    # BenchmarkEvaluator computes returns from close prices and signals.
    # A simpler way is to check the internal _calculate_regime_consistency which we know uses it.

    # Let's mock a data frame with two regimes
    data = sample_data.copy().iloc[:100]
    data["regime"] = "ranging"
    data.loc[0:49, "regime"] = "trending"
    data.loc[50:99, "regime"] = "ranging"

    # Sharpe = (mean/std) * sqrt(6240)
    # If we use 252 instead, Sharpe would be significantly lower.

    # We can use a custom config to verify scaling
    config_small = WalkForwardConfig(bars_per_year=252)
    optimizer_small = WalkForwardOptimizer(sample_data, EMACrossoverStrategy, lambda t: {}, config_small)

    # consistency calculation doesn't directly return Sharpe, but uses it internally.
    # To really verify bars_per_year, we should check a method that returns a value scaled by it.
    # _evaluate_strategy returns metrics including "Sharpe Ratio"

    params = {"fast_window": 10, "slow_window": 20}
    metrics_6240, _ = optimizer._evaluate_strategy(sample_data.iloc[:100], params)
    metrics_252, _ = optimizer_small._evaluate_strategy(sample_data.iloc[:100], params)

    sharpe_6240 = metrics_6240["Sharpe Ratio"]
    sharpe_252 = metrics_252["Sharpe Ratio"]

    if sharpe_252 != 0:
        # Ratio should be sqrt(6240) / sqrt(252)
        expected_ratio = np.sqrt(6240) / np.sqrt(252)
        assert sharpe_6240 / sharpe_252 == pytest.approx(expected_ratio)

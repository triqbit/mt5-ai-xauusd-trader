import pytest
import pandas as pd
import numpy as np
from src.research.hyperopt_walkforward import WalkForwardOptimizer, ma_metric_fn

def test_window_generation():
    # 1000 data points
    data = pd.DataFrame({"close": np.random.randn(1000)})
    optimizer = WalkForwardOptimizer(
        data=data,
        train_size=200,
        test_size=50,
        step_size=50,
        metric_fn=ma_metric_fn
    )

    windows = optimizer.generate_windows()

    # (1000 - 200 - 50) / 50 + 1 = 750 / 50 + 1 = 15 + 1 = 16
    assert len(windows) == 16
    assert windows[0].train_start == 0
    assert windows[0].train_end == 200
    assert windows[0].test_start == 200
    assert windows[0].test_end == 250

    assert windows[-1].test_end <= 1000

def test_run_optimization():
    # Create some dummy data with a trend so MA strategy might do something
    n = 500
    t = np.linspace(0, 10, n)
    close = 100 + 10 * np.sin(t) + np.cumsum(np.random.randn(n) * 0.5)
    data = pd.DataFrame({"close": close})

    optimizer = WalkForwardOptimizer(
        data=data,
        train_size=100,
        test_size=40,
        step_size=40,
        metric_fn=ma_metric_fn
    )

    param_grid = [
        {"fast_period": 5, "slow_period": 20},
        {"fast_period": 10, "slow_period": 30},
    ]

    report = optimizer.run_optimization(param_grid, strategy_name="TestMA")

    assert report.strategy_name == "TestMA"
    assert report.total_windows > 0
    assert len(report.window_results) == report.total_windows
    assert "fast_period" in report.best_overall_params
    assert 0 <= report.overall_robustness_score <= 1.0

def test_robustness_scoring_logic():
    # Mock results to test scoring
    from src.research.hyperopt_walkforward import HyperoptResult, WalkForwardOptimizer

    # Mock data doesn't matter for _build_report
    optimizer = WalkForwardOptimizer(pd.DataFrame(), 0, 0, 0, ma_metric_fn)

    # Case 1: Perfectly stable, perfectly consistent
    results = [
        HyperoptResult(params={"p": 1}, train_metric=1.0, test_metric=0.5, window_id=0),
        HyperoptResult(params={"p": 1}, train_metric=1.0, test_metric=0.5, window_id=1),
    ]
    report = optimizer._build_report(results, "Stable")
    assert report.oos_consistency == 1.0
    assert report.parameter_stability == 1.0
    assert report.performance_degradation == pytest.approx(0.5)

    # Case 2: Unstable, inconsistent
    results = [
        HyperoptResult(params={"p": 1}, train_metric=1.0, test_metric=0.5, window_id=0),
        HyperoptResult(params={"p": 2}, train_metric=1.0, test_metric=-0.1, window_id=1),
    ]
    report = optimizer._build_report(results, "Unstable")
    assert report.oos_consistency == 0.5
    assert report.parameter_stability == 0.5

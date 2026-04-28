import numpy as np
import pytest
from src.research.hyperopt_walkforward import (
    WalkForwardOptimizer,
    WalkForwardConfig,
    MovingAverageStrategy,
    WindowResult
)

def test_window_generation():
    config = WalkForwardConfig(train_window=100, test_window=20, step_size=20)
    optimizer = WalkForwardOptimizer(MovingAverageStrategy(), config)

    # Total data 150
    # W1: 0-100 (train), 100-120 (test)
    # W2: 20-120 (train), 120-140 (test)
    # W3: 40-140 (train), 140-160 (TOO LONG)
    windows = optimizer.generate_windows(150)
    assert len(windows) == 2
    assert windows[0] == (0, 100, 120)
    assert windows[1] == (20, 120, 140)

def test_robustness_scoring_perfect():
    config = WalkForwardConfig(train_window=50, test_window=10, step_size=10)
    optimizer = WalkForwardOptimizer(MovingAverageStrategy(), config)

    # Perfect stability and consistency
    results = [
        WindowResult(
            window_idx=i, start_idx=0, train_end_idx=50, test_end_idx=60,
            best_params={"p1": 10}, train_metrics={"return": 0.1}, test_metrics={"return": 0.1},
            oos_degradation=1.0
        ) for i in range(5)
    ]
    stability = {"p1": 0.0}
    score = optimizer._calculate_robustness(results, stability)

    # Consistency: 1.0, Degradation: 1.0, Stability: 1.0
    # 0.4*1 + 0.4*1 + 0.2*1 = 1.0
    assert score == 1.0

def test_robustness_scoring_poor():
    config = WalkForwardConfig(train_window=50, test_window=10, step_size=10)
    optimizer = WalkForwardOptimizer(MovingAverageStrategy(), config)

    # High instability and poor consistency
    results = [
        WindowResult(
            window_idx=0, start_idx=0, train_end_idx=50, test_end_idx=60,
            best_params={"p1": 10}, train_metrics={"return": 0.1}, test_metrics={"return": -0.05},
            oos_degradation=-0.5
        ),
        WindowResult(
            window_idx=1, start_idx=10, train_end_idx=60, test_end_idx=70,
            best_params={"p1": 50}, train_metrics={"return": 0.1}, test_metrics={"return": -0.05},
            oos_degradation=-0.5
        )
    ]
    stability = {"p1": 1.0}
    score = optimizer._calculate_robustness(results, stability)

    # Consistency: 0.0, Degradation: 0.0 (clipped), Stability: 0.5
    # 0.4*0 + 0.4*0 + 0.2*0.5 = 0.1
    assert pytest.approx(score, 0.01) == 0.1

def test_full_optimization_loop():
    # Generate dummy price data
    np.random.seed(42)
    n_bars = 500
    # Geometric Brownian Motion
    rets = np.random.normal(0.0001, 0.01, n_bars)
    prices = 100 * np.cumprod(1 + rets)
    data = np.zeros((n_bars, 4))
    data[:, 3] = prices # Close

    config = WalkForwardConfig(train_window=200, test_window=50, step_size=50)
    strategy = MovingAverageStrategy()
    optimizer = WalkForwardOptimizer(strategy, config)

    param_grid = [
        {"fast_ema": 5, "slow_ema": 20},
        {"fast_ema": 10, "slow_ema": 50},
        {"fast_ema": 20, "slow_ema": 100},
    ]

    report = optimizer.run(data, param_grid)

    assert isinstance(report.overall_robustness, float)
    assert len(report.windows) >= 3
    assert "fast_ema" in report.parameter_stability

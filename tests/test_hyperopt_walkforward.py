"""
Tests for walk-forward optimization and robustness scoring.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from src.research.hyperopt_walkforward import WalkForwardOptimizer, Strategy, WindowMetrics


class MockStrategy:
    """A simple strategy for testing."""
    def run(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
        # Return dummy metrics based on params
        # Higher 'val' param = higher sharpe
        val = params.get("val", 1.0)
        return {
            "sharpe_ratio": val,
            "total_return": val * 10,
            "max_drawdown": 0.1,
            "win_rate": 0.6,
            "profit_factor": 2.0,
            "num_trades": 20,
            "consistency_score": 0.5
        }


@pytest.fixture
def dummy_data():
    dates = pd.date_range(start="2023-01-01", periods=1000, freq="h")
    df = pd.DataFrame(
        np.random.randn(1000, 4),
        index=dates,
        columns=["open", "high", "low", "close"]
    )
    return df


def test_window_generation(dummy_data):
    optimizer = WalkForwardOptimizer(
        strategy=MockStrategy(),
        data=dummy_data,
        param_space=lambda t: {"val": t.suggest_float("val", 0, 1)},
    )

    # 1000 bars total
    # train 400, test 100, step 100
    # Window 1: 0-400 (train), 400-500 (test)
    # Window 2: 100-500 (train), 500-600 (test)
    # Window 3: 200-600 (train), 600-700 (test)
    # Window 4: 300-700 (train), 700-800 (test)
    # Window 5: 400-800 (train), 800-900 (test)
    # Window 6: 500-900 (train), 900-1000 (test)
    windows = optimizer.generate_windows(400, 100, 100, expanding=False)
    assert len(windows) == 6

    train0, test0 = windows[0]
    assert len(train0) == 400
    assert len(test0) == 100
    assert train0.index[-1] < test0.index[0]


def test_expanding_window_generation(dummy_data):
    optimizer = WalkForwardOptimizer(
        strategy=MockStrategy(),
        data=dummy_data,
        param_space=lambda t: {"val": t.suggest_float("val", 0, 1)},
    )

    windows = optimizer.generate_windows(400, 100, 100, expanding=True)
    assert len(windows) == 6

    # Window 0: 0-400
    # Window 1: 0-500
    # Window 2: 0-600
    assert len(windows[0][0]) == 400
    assert len(windows[1][0]) == 500
    assert len(windows[2][0]) == 600


def test_robustness_calculation():
    optimizer = WalkForwardOptimizer(MockStrategy(), pd.DataFrame(), lambda t: {})

    is_metrics = WindowMetrics(
        sharpe_ratio=2.0, total_return=20, max_drawdown=0.1,
        win_rate=0.6, profit_factor=2.0, num_trades=20
    )
    oos_metrics = WindowMetrics(
        sharpe_ratio=1.8, total_return=15, max_drawdown=0.12,
        win_rate=0.55, profit_factor=1.8, num_trades=15
    )

    score = optimizer._calculate_robustness(is_metrics, oos_metrics, stability_score=0.9)
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # Should be reasonably high for these metrics


def test_optimization_flow(dummy_data):
    def param_space(trial):
        return {"val": trial.suggest_float("val", 1.0, 2.0)}

    optimizer = WalkForwardOptimizer(
        strategy=MockStrategy(),
        data=dummy_data,
        param_space=param_space,
        n_trials=5
    )

    summary = optimizer.optimize(train_size_bars=800, test_size_bars=100, step_size_bars=100)

    assert summary.total_windows > 0
    assert len(summary.windows) == summary.total_windows
    assert summary.avg_oos_sharpe >= 1.0
    assert summary.robustness_index > 0

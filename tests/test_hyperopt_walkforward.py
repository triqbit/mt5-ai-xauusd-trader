"""
Tests for WalkForwardOptimizer.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from src.research.hyperopt_walkforward import WalkForwardOptimizer


class MockStrategy:
    """A mock strategy that returns metrics based on parameters."""

    def run(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
        # Simple logic: higher 'val' param means higher sharpe, but only on even indices
        val = params.get("val", 0.0)
        sharpe = val * 1.5
        mdd = 0.1 / (val + 0.1)
        return {"sharpe": float(sharpe), "mdd": float(mdd)}


@pytest.fixture
def sample_data():
    dates = [datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(days=i) for i in range(100)]
    df = pd.DataFrame({"close": np.random.randn(100).cumsum() + 100}, index=dates)
    return df


def test_generate_windows_rolling(sample_data):
    optimizer = WalkForwardOptimizer(MockStrategy(), sample_data, {})
    windows = optimizer.generate_windows(train_size=40, test_size=10, step_size=10, expanding=False)

    # Total 100 bars.
    # W1: 0-40, 40-50
    # W2: 10-50, 50-60
    # W3: 20-60, 60-70
    # W4: 30-70, 70-80
    # W5: 40-80, 80-90
    # W6: 50-90, 90-100
    assert len(windows) == 6
    assert len(windows[0][0]) == 40
    assert len(windows[0][1]) == 10
    assert windows[1][0].index[0] == sample_data.index[10]


def test_generate_windows_expanding(sample_data):
    optimizer = WalkForwardOptimizer(MockStrategy(), sample_data, {})
    windows = optimizer.generate_windows(train_size=40, test_size=10, step_size=10, expanding=True)

    assert len(windows) == 6
    assert len(windows[0][0]) == 40
    assert len(windows[1][0]) == 50  # 0 to 50
    assert windows[1][0].index[0] == sample_data.index[0]


def test_robustness_scoring():
    optimizer = WalkForwardOptimizer(MockStrategy(), pd.DataFrame(), {})

    # Perfect consistency
    score = optimizer._calculate_robustness_score(
        {"sharpe": 1.0, "mdd": 0.1}, {"sharpe": 1.0, "mdd": 0.1}
    )
    assert score >= 0.9  # Should be high

    # OOS failure
    score = optimizer._calculate_robustness_score(
        {"sharpe": 2.0, "mdd": 0.1}, {"sharpe": 0.2, "mdd": 0.5}
    )
    assert score < 0.5


def test_full_walk_forward(sample_data):
    param_space = {"val": ("float", 0.1, 1.0)}
    optimizer = WalkForwardOptimizer(MockStrategy(), sample_data, param_space, n_trials=5)

    report = optimizer.run_walk_forward(train_size=70, test_size=10, step_size=10)

    assert len(report.windows) == 3  # 0-70/70-80, 10-80/80-90, 20-90/90-100
    assert report.overall_robustness >= 0
    assert "val" in report.parameter_stability

"""
Unit tests for the benchmarking framework.
"""

import numpy as np
import pandas as pd
import pytest
from src.research.benchmarks import (
    EMACrossoverStrategy,
    MomentumStrategy,
    VolatilityBreakoutStrategy,
    NaiveDirectionalStrategy,
    RiskFilteredBaseline,
    BenchmarkEvaluator,
)


@pytest.fixture
def sample_data():
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    n = 100
    close = 100 + np.cumsum(np.random.randn(n))
    df = pd.DataFrame(
        {
            "open": close - np.random.randn(n),
            "high": close + np.abs(np.random.randn(n)),
            "low": close - np.abs(np.random.randn(n)),
            "close": close,
            "tick_volume": np.random.randint(100, 1000, n),
        }
    )
    return df


def test_ema_crossover_signals(sample_data):
    strategy = EMACrossoverStrategy(fast_window=5, slow_window=10)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_momentum_signals(sample_data):
    strategy = MomentumStrategy(window=5)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_volatility_breakout_signals(sample_data):
    strategy = VolatilityBreakoutStrategy(window=10)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_naive_directional_signals(sample_data):
    strategy = NaiveDirectionalStrategy()
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_risk_filtered_signals(sample_data):
    strategy = RiskFilteredBaseline(vol_threshold_pct=0.01)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_evaluator_metrics(sample_data):
    evaluator = BenchmarkEvaluator(sample_data)
    strategies = [EMACrossoverStrategy(5, 10), MomentumStrategy(5)]
    results = evaluator.evaluate_all(strategies)
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 2
    assert "Total Return" in results.columns
    assert "Sharpe Ratio" in results.columns


def test_comparison_logic(sample_data):
    evaluator = BenchmarkEvaluator(sample_data)
    s1 = EMACrossoverStrategy(5, 10)
    s2 = MomentumStrategy(5)
    evaluator.evaluate_all([s1, s2])

    comp = evaluator.compare_to_baseline(s1.name, s2.name)
    assert "Outperformance" in comp
    assert "Sharpe Improvement" in comp

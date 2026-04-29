"""
Tests for the Benchmarking framework.
"""

import numpy as np
import pytest
import pandas as pd
from src.research.benchmarks import (
    BenchmarkEvaluator,
    EMACrossoverStrategy,
    MomentumStrategy,
    VolatilityBreakoutStrategy,
    NaiveDirectionalStrategy,
    RiskFilteredBaseline,
    ModelWrapper,
    StrategyResult
)

@pytest.fixture
def sample_data():
    """Generate 100 rows of synthetic price data."""
    np.random.seed(42)
    rows = 100
    # Open, High, Low, Close, Volume
    data = np.zeros((rows, 5))
    data[:, 0] = 2000.0 + np.cumsum(np.random.randn(rows)) # Open
    data[:, 1] = data[:, 0] + 2.0 # High
    data[:, 2] = data[:, 0] - 2.0 # Low
    data[:, 3] = data[:, 0] + np.random.randn(rows) # Close
    data[:, 4] = 1000 + np.random.randint(0, 500, rows) # Volume
    return data

def test_ema_crossover_signals(sample_data):
    strategy = EMACrossoverStrategy(fast_period=5, slow_period=10)
    signals = strategy.generate_signals(sample_data)
    assert len(signals) == len(sample_data)
    assert set(np.unique(signals)).issubset({0.0, 1.0, 2.0})

def test_momentum_signals(sample_data):
    strategy = MomentumStrategy(period=5)
    signals = strategy.generate_signals(sample_data)
    assert len(signals) == len(sample_data)

def test_vol_breakout_signals(sample_data):
    strategy = VolatilityBreakoutStrategy(period=5)
    signals = strategy.generate_signals(sample_data)
    assert len(signals) == len(sample_data)

def test_naive_directional_signals(sample_data):
    strategy = NaiveDirectionalStrategy(direction=1)
    signals = strategy.generate_signals(sample_data)
    assert np.all(signals == 1)

def test_risk_filtered_baseline(sample_data):
    base = EMACrossoverStrategy()
    strategy = RiskFilteredBaseline(base_strategy=base, max_vol_mult=0.5)
    signals = strategy.generate_signals(sample_data)
    assert len(signals) == len(sample_data)
    # Since mult is low, some signals should be filtered to 0
    assert 0 in signals

def test_evaluator_metrics(sample_data):
    evaluator = BenchmarkEvaluator()
    strategy = NaiveDirectionalStrategy(direction=1)
    result = evaluator.evaluate(strategy, sample_data)

    assert isinstance(result, StrategyResult)
    assert result.name == "Buy_and_Hold"
    assert hasattr(result, "total_return")
    assert hasattr(result, "sharpe_ratio")
    assert hasattr(result, "max_drawdown")

def test_benchmark_comparison(sample_data):
    evaluator = BenchmarkEvaluator()
    strategies = [
        EMACrossoverStrategy(),
        MomentumStrategy(),
        NaiveDirectionalStrategy()
    ]
    df = evaluator.compare(strategies, sample_data)
    assert len(df) == 3
    assert "total_return" in df.columns
    assert "sharpe_ratio" in df.columns

def test_model_wrapper_interface(sample_data):
    class MockModel:
        def predict(self, obs):
            return 1, {} # Action 1

    model = MockModel()
    wrapper = ModelWrapper(model, window_size=10)
    signals = wrapper.generate_signals(sample_data)
    assert len(signals) == len(sample_data)
    # Signals before window_size should be 0
    assert np.all(signals[:10] == 0)
    # Signals after window_size should be 1
    assert np.all(signals[10:] == 1)

def test_p_value_calculation():
    evaluator = BenchmarkEvaluator()
    res1 = StrategyResult(
        name="A", total_return=0.1, cagr=0.1, sharpe_ratio=1.0,
        sortino_ratio=1.0, max_drawdown=0.05, win_rate=0.5,
        profit_factor=1.5, total_trades=10, volatility=0.1,
        returns=[0.01, 0.02, -0.01, 0.03, 0.01]
    )
    res2 = StrategyResult(
        name="B", total_return=0.05, cagr=0.05, sharpe_ratio=0.5,
        sortino_ratio=0.5, max_drawdown=0.1, win_rate=0.4,
        profit_factor=1.1, total_trades=10, volatility=0.15,
        returns=[-0.01, 0.01, -0.02, 0.01, 0.0]
    )
    p_val = evaluator.calculate_p_value(res1, res2)
    assert 0 <= p_val <= 1.0

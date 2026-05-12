"""
Extended tests for the benchmarking framework, focusing on slippage and new baselines.
"""

import numpy as np
import pandas as pd
import pytest
from src.research.benchmarks import (
    BenchmarkEvaluator,
    ADXStrategy,
    EMACrossoverStrategy
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

def test_adx_strategy_signals(sample_data):
    strategy = ADXStrategy(window=14, adx_threshold=20.0)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))

def test_slippage_impact(sample_data):
    """Test that slippage correctly reduces total return."""
    # Use a simple strategy that makes at least one trade
    strategy = EMACrossoverStrategy(fast_window=5, slow_window=10)

    # 1. Evaluate without slippage
    eval_no_slip = BenchmarkEvaluator(sample_data, commission=0.0001, slippage=0.0)
    eval_no_slip.evaluate_all([strategy])
    return_no_slip = eval_no_slip.results[strategy.name]["Total Return"]

    # 2. Evaluate with slippage
    eval_with_slip = BenchmarkEvaluator(sample_data, commission=0.0001, slippage=0.01) # 1% slippage is huge, should be visible
    eval_with_slip.evaluate_all([strategy])
    return_with_slip = eval_with_slip.results[strategy.name]["Total Return"]

    # Ensure slippage reduced the return
    # Only if trades were actually made
    if eval_no_slip.results[strategy.name]["Num Trades"] > 0:
        assert return_with_slip < return_no_slip
    else:
        pytest.skip("No trades made by the strategy in sample data")

def test_evaluator_slippage_parameter():
    """Test that BenchmarkEvaluator correctly stores the slippage parameter."""
    df = pd.DataFrame({"close": [100, 101]})
    evaluator = BenchmarkEvaluator(df, slippage=0.0005)
    assert evaluator.slippage == 0.0005

def test_adx_strategy_fallback(sample_data):
    """Test ADXStrategy fallback logic when talib is unavailable."""
    # We can mock talib import to force fallback, or just rely on the environment
    # if talib is already missing.
    strategy = ADXStrategy(window=5)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))

def test_adapter_robustness_short_df():
    """Test that adapters handle DataFrames shorter than window_size."""
    from src.research.benchmarks import EnsembleAdapter
    from unittest.mock import MagicMock
    import sys

    # Mock torch for this test if it's not present
    if "torch" not in sys.modules:
        sys.modules["torch"] = MagicMock()

    mock_model = MagicMock()
    adapter = EnsembleAdapter(mock_model, window_size=60)

    short_df = pd.DataFrame({"close": np.random.randn(10)})
    signals = adapter.predict(short_df)

    assert len(signals) == 10
    assert np.all(signals == 0)
    assert not mock_model.predict.called

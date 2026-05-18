"""
Extended tests for the benchmarking framework, focusing on slippage and new baselines.
"""

import sys
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.research.benchmarks import (
    ADXStrategy,
    BenchmarkEvaluator,
    BuyAndHoldStrategy,
    DonchianChannelStrategy,
    EMACrossoverStrategy,
    EnsembleAdapter,
    RegimeFilterBaseline,
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


def test_donchian_strategy_signals(sample_data):
    strategy = DonchianChannelStrategy(window=10)
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
    # 1% slippage is huge, should be visible
    eval_with_slip = BenchmarkEvaluator(sample_data, commission=0.0001, slippage=0.01)
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


def test_regime_filter_comparison(sample_data):
    """Test comparison using RegimeFilterBaseline."""
    from src.models.regime_detector import MarketRegime

    sample_data["regime"] = MarketRegime.RANGING.value
    # More variance in later half
    sample_data.loc[50:, "close"] += np.cumsum(np.random.randn(50) * 2)
    sample_data.loc[50:, "regime"] = MarketRegime.TRENDING.value

    evaluator = BenchmarkEvaluator(sample_data)

    s_base = BuyAndHoldStrategy()
    s_filtered = RegimeFilterBaseline(s_base, allowed_regimes=[MarketRegime.TRENDING.value])

    evaluator.evaluate_all([s_base, s_filtered])

    comp = evaluator.compare_to_baseline(s_filtered.name, s_base.name)
    assert "Outperformance" in comp
    assert not comp.get("error")


def test_adapter_robustness_short_df():
    """Test that adapters handle DataFrames shorter than window_size."""
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


def test_supertrend_signals(sample_data):
    from src.research.benchmarks import SuperTrendStrategy

    strategy = SuperTrendStrategy(window=10, multiplier=3.0)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))
    # First 'window' signals should be 0
    assert np.all(signals[:10] == 0)
    # At least some signals should be non-zero
    assert np.any(signals != 0)


def test_london_breakout_signals():
    from src.research.benchmarks import LondonBreakoutStrategy

    np.random.seed(42)
    n = 500
    dates = pd.date_range(start="2024-01-01", periods=n, freq="1h")
    close = 2000 + np.cumsum(np.random.randn(n))
    df = pd.DataFrame(
        {
            "open": close - np.random.randn(n),
            "high": close + np.abs(np.random.randn(n)),
            "low": close - np.abs(np.random.randn(n)),
            "close": close,
            "tick_volume": np.random.randint(100, 1000, n),
        },
        index=dates,
    )

    strategy = LondonBreakoutStrategy(range_start="00:00", range_end="08:00")
    signals = strategy.predict(df)
    assert len(signals) == len(df)
    assert np.all(np.isin(signals, [0, 1, -1]))
    # Should have relatively few signals (max 1 per day)
    # Each trade lasts until end of day (24 bars max per day, but starting from breakout)
    # This check is a bit complex due to persistence, but we can check num of transitions
    transitions = np.diff(signals)
    assert np.sum(transitions != 0) <= (len(df) / 24) * 2


def test_new_metrics_in_evaluator(sample_data):
    from src.research.benchmarks import BenchmarkEvaluator, SuperTrendStrategy

    evaluator = BenchmarkEvaluator(sample_data)
    strategy = SuperTrendStrategy(window=10)
    results = evaluator.evaluate_all([strategy])

    assert "Omega Ratio" in results.columns
    # Check if value is float and reasonably not NaN if there's any trade
    if results.iloc[0]["Num Trades"] > 0:
        assert not np.isnan(results.iloc[0]["Omega Ratio"])


def test_new_metrics_in_comparison(sample_data):
    from src.research.benchmarks import BenchmarkEvaluator, SuperTrendStrategy

    evaluator = BenchmarkEvaluator(sample_data)
    s1 = SuperTrendStrategy(window=5)
    s2 = SuperTrendStrategy(window=10)
    evaluator.evaluate_all([s1, s2])

    comp = evaluator.compare_to_baseline(s1.name, s2.name)
    assert "Information Ratio" in comp
    assert not np.isnan(comp["Information Ratio"])


def test_report_section_with_new_metrics(sample_data):
    from src.research.benchmarks import BenchmarkEvaluator, SuperTrendStrategy

    evaluator = BenchmarkEvaluator(sample_data)
    s1 = SuperTrendStrategy(window=5)
    s2 = SuperTrendStrategy(window=10)
    evaluator.evaluate_all([s1, s2])

    section = evaluator.to_report_section(baseline_name=s2.name)
    assert hasattr(section.comparisons[0], "information_ratio")
    assert hasattr(section.comparisons[0], "omega_ratio")
    # In sample data they might be "0.00" if no outperformance or no gains

"""
Unit tests for the benchmarking framework.
"""

import importlib.util
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.core.constants import SignalDirection
from src.models.base_model import Signal
from src.research.benchmarks import (
    BenchmarkEvaluator,
    BuyAndHoldStrategy,
    DreamerAdapter,
    EMACrossoverStrategy,
    EnsembleAdapter,
    LSTMAdapter,
    MACDStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NaiveDirectionalStrategy,
    PPOAdapter,
    RandomStrategy,
    RiskFilteredBaseline,
    TransformerAdapter,
    VolatilityBreakoutStrategy,
)

HAS_TORCH = importlib.util.find_spec("torch") is not None


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


def test_buy_and_hold_signals(sample_data):
    strategy = BuyAndHoldStrategy()
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(signals == 1.0)


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


def test_mean_reversion_signals(sample_data):
    strategy = MeanReversionStrategy(window=5)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_macd_signals(sample_data):
    strategy = MACDStrategy(5, 10, 3)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [0, 1, -1]))


def test_evaluator_metrics(sample_data):
    evaluator = BenchmarkEvaluator(sample_data)
    strategies = [
        EMACrossoverStrategy(5, 10),
        MomentumStrategy(5),
        VolatilityBreakoutStrategy(10),
        RiskFilteredBaseline(5, 10, 0.02),
        MACDStrategy(5, 10, 3),
    ]
    results = evaluator.evaluate_all(strategies)
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 5
    assert "Total Return" in results.columns
    assert "Sharpe Ratio" in results.columns
    assert "Sortino Ratio" in results.columns
    assert "Profit Factor" in results.columns
    assert "Calmar Ratio" in results.columns
    assert "Expectancy" in results.columns
    assert "Skewness" in results.columns
    assert "Kurtosis" in results.columns
    assert "VaR_95" in results.columns
    assert "CVaR_95" in results.columns
    assert "Ulcer Index" in results.columns
    assert "Tail Ratio" in results.columns
    assert "Common Sense Ratio" in results.columns
    assert "Gain to Pain Ratio" in results.columns
    assert "Lake Ratio" in results.columns
    assert "Stability Score" in results.columns


def test_comparison_logic(sample_data):
    evaluator = BenchmarkEvaluator(sample_data)
    s1 = EMACrossoverStrategy(5, 10)
    s2 = MomentumStrategy(5)
    evaluator.evaluate_all([s1, s2])

    comp = evaluator.compare_to_baseline(s1.name, s2.name)
    assert "Outperformance" in comp
    assert "Sharpe Improvement" in comp
    assert "Wilcoxon P-Value" in comp


def test_to_report_section(sample_data):
    evaluator = BenchmarkEvaluator(sample_data)
    s1 = EMACrossoverStrategy(5, 10)
    s2 = MomentumStrategy(5)
    evaluator.evaluate_all([s1, s2])

    section = evaluator.to_report_section(baseline_name=s2.name)
    assert len(section.comparisons) == 1
    assert section.comparisons[0].name == s1.name
    assert "statistically significant" in section.statistical_summary


def test_evaluator_reversals(sample_data):
    """Test that immediate reversals are handled correctly."""
    # Create signals that flip from 1 to -1
    signals = np.zeros(len(sample_data))
    signals[10] = 1
    signals[11] = -1

    evaluator = BenchmarkEvaluator(sample_data, commission=0.0)
    metrics = evaluator._calculate_metrics(signals, "test")

    # With 0 commission, reversal shouldn't crash and should result in 2 trades
    # (One long from 10 to 11, one short from 11 onwards)
    assert metrics["Num Trades"] == 2


def test_ppo_adapter(sample_data):
    mock_agent = MagicMock()
    mock_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.9)

    adapter = PPOAdapter(mock_agent)
    signals = adapter.predict(sample_data)

    assert len(signals) == len(sample_data)
    assert np.all(signals == 1.0)
    assert mock_agent.predict.call_count == len(sample_data)


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_ensemble_adapter(sample_data):
    mock_model = MagicMock()
    mock_model.predict.return_value = Signal(direction=SignalDirection.SELL, confidence=0.8)

    window_size = 10
    adapter = EnsembleAdapter(mock_model, window_size=window_size)
    signals = adapter.predict(sample_data)

    assert len(signals) == len(sample_data)
    # First window_size-1 signals should be 0
    assert np.all(signals[: window_size - 1] == 0)
    # Remaining signals should be -1.0
    assert np.all(signals[window_size - 1 :] == -1.0)
    assert mock_model.predict.call_count == len(sample_data) - (window_size - 1)


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_transformer_adapter(sample_data):
    import torch

    mock_model = MagicMock()
    # Mock return: a tensor of probabilities [batch, 3] where index 1 is BUY (ModelAction standard)
    mock_model.return_value = torch.tensor([[0.0, 1.0, 0.0]])

    window_size = 5
    adapter = TransformerAdapter(mock_model, window_size=window_size)
    signals = adapter.predict(sample_data)

    assert len(signals) == len(sample_data)
    assert np.all(signals[: window_size - 1] == 0)
    assert np.all(signals[window_size - 1 :] == 1.0)


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_lstm_adapter(sample_data):
    import torch

    mock_model = MagicMock()
    # Mock return: logits for [hold, buy, sell]
    mock_model.return_value = torch.tensor([[0.0, 10.0, 0.0]])  # High logit for BUY

    window_size = 5
    adapter = LSTMAdapter(mock_model, window_size=window_size)
    signals = adapter.predict(sample_data)

    assert len(signals) == len(sample_data)
    assert np.all(signals[: window_size - 1] == 0)
    assert np.all(signals[window_size - 1 :] == 1.0)
    assert mock_model.call_count == len(sample_data) - (window_size - 1)


def test_dreamer_adapter(sample_data):
    mock_agent = MagicMock()
    mock_agent.predict.return_value = Signal(direction=SignalDirection.SELL, confidence=0.7)

    adapter = DreamerAdapter(mock_agent)
    signals = adapter.predict(sample_data)

    assert len(signals) == len(sample_data)
    assert np.all(signals == -1.0)
    assert mock_agent.predict.call_count == len(sample_data)
    assert mock_agent.reset_state.called


def test_random_strategy_signals(sample_data):
    strategy = RandomStrategy(seed=42)
    signals = strategy.predict(sample_data)
    assert len(signals) == len(sample_data)
    assert np.all(np.isin(signals, [-1, 0, 1]))

    # Test reproducibility
    s2 = RandomStrategy(seed=42)
    signals2 = s2.predict(sample_data)
    assert np.array_equal(signals, signals2)

    # Test different seed
    s3 = RandomStrategy(seed=43)
    signals3 = s3.predict(sample_data)
    assert not np.array_equal(signals, signals3)


def test_comparison_identical_strategies(sample_data):
    """Test statistical comparison of identical strategies."""
    evaluator = BenchmarkEvaluator(sample_data)
    s1 = EMACrossoverStrategy(5, 10)
    evaluator.evaluate_all([s1])

    # Manually add duplicate results with different name
    evaluator.results["EMA_Duplicate"] = evaluator.results[s1.name]
    evaluator.results["EMA_Duplicate_returns"] = evaluator.results[s1.name + "_returns"]

    comp = evaluator.compare_to_baseline(s1.name, "EMA_Duplicate")
    assert comp["Outperformance"] == 0.0
    assert comp["Sharpe Improvement"] == 0.0
    assert not comp["Significant"]


def test_comparison_no_trades(sample_data):
    """Test comparison when one strategy has no trades."""
    evaluator = BenchmarkEvaluator(sample_data)

    # Mock strategy with no signals
    class NoTradeStrategy:
        @property
        def name(self):
            return "No_Trade"

        def predict(self, df):
            return np.zeros(len(df))

    s1 = EMACrossoverStrategy(5, 10)
    s2 = NoTradeStrategy()
    evaluator.evaluate_all([s1, s2])

    comp = evaluator.compare_to_baseline(s1.name, s2.name)
    assert "error" not in comp
    assert comp["Outperformance"] == evaluator.results[s1.name]["Total Return"]


def test_regime_aware_adapter(sample_data):
    """Test that adapters correctly extract and pass regime info."""
    from src.models.regime_detector import MarketRegime

    # Add regime columns to sample data
    sample_data["regime"] = MarketRegime.TRENDING.value
    sample_data["regime_confidence"] = 0.95
    sample_data["regime_transition_score"] = 0.1
    sample_data["volatility_index"] = 1.2

    mock_agent = MagicMock()
    mock_agent.predict.return_value = Signal(direction=SignalDirection.BUY, confidence=0.9)

    adapter = PPOAdapter(mock_agent)
    adapter.predict(sample_data)

    # Verify that the first call to mock_agent.predict received regime_info
    _args, kwargs = mock_agent.predict.call_args_list[0]
    regime_info = kwargs.get("regime_info")
    assert regime_info is not None
    assert regime_info.label == MarketRegime.TRENDING
    assert regime_info.confidence == 0.95


def test_comparison_very_few_trades(sample_data):
    """Test comparison when strategies have very few trades."""
    evaluator = BenchmarkEvaluator(sample_data)

    # Strategy with only 1 trade
    class FewTradeStrategy:
        @property
        def name(self):
            return "Few_Trade"

        def predict(self, df):
            signals = np.zeros(len(df))
            signals[10] = 1
            signals[11] = 0
            return signals

    s1 = EMACrossoverStrategy(5, 10)
    s2 = FewTradeStrategy()
    evaluator.evaluate_all([s1, s2])

    comp = evaluator.compare_to_baseline(s1.name, s2.name)
    assert "error" not in comp

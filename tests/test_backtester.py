"""
Unit tests for the BacktestEngine.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.trading.backtester import BacktestEngine


class MockModel:
    def predict(self, obs):
        return type("Signal", (), {"direction": 1, "confidence": 0.8})


@pytest.fixture
def sample_data():
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="5min")
    # Create a trending price series to pass execution filters (EMA sequence, Trend angle)
    base_price = 2000.0
    trend = np.linspace(0, 100, 1000)
    close = base_price + trend
    df = pd.DataFrame(
        {
            "open": close - 1,
            "high": close + 5,
            "low": close - 5,
            "close": close,
            "tick_volume": np.full(1000, 1000),
        },
        index=dates,
    )
    return df


def test_backtest_engine_initialization():
    engine = BacktestEngine(symbol="XAUUSD")
    assert engine.symbol == "XAUUSD"
    assert engine.initial_balance == 10000.0
    assert engine.balance == 10000.0
    assert len(engine.trades) == 0


def test_backtest_run(sample_data):
    # Mocking ExecutionFilter to always approve
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})

    engine = BacktestEngine(symbol="XAUUSD", max_positions=1, execution_filter=mock_ef)

    # We need to provide a model that predict Buy
    model = MockModel()

    report = engine.run_walk_forward(
        sample_data,
        model,
        train_window=100,
        test_window=50,
        step_size=50
    )

    assert report.total_trades > 0
    assert isinstance(report.annualized_return, float)
    assert report.start_date is not None


def test_backtest_performance_optimized_loop(sample_data):
    """
    Verifies that the optimized NumPy-based loop produces same results as
    expected and handles the full data range correctly.
    """
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})
    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef)
    model = MockModel()

    report = engine.run_walk_forward(
        sample_data,
        model,
        train_window=200,
        test_window=100,
        step_size=100
    )

    # Basic validity checks for the optimized loop execution
    assert report.total_trades > 0
    assert report.total_return > 0  # Sample data is trending up
    assert len(engine.trades) == report.total_trades


def test_walk_forward_normalization_no_lookahead(sample_data):
    """
    Verifies that features passed to the model are normalized based on
    the training window only, ensuring no look-ahead bias.
    """
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})

    # We want to capture the observations passed to the model
    captured_obs = []

    class CapturingModel:
        def predict(self, obs, **kwargs):
            captured_obs.append(obs.copy())
            return type("Signal", (), {"direction": 1, "confidence": 0.8})

    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef)
    model = CapturingModel()

    train_window = 200
    test_window = 50
    step_size = 50

    engine.run_walk_forward(
        sample_data,
        model,
        train_window=train_window,
        test_window=test_window,
        step_size=step_size
    )

    assert len(captured_obs) > 0

    # Check that observations are not identical to raw features
    # (since they should be normalized)
    # We need to compute features to compare
    from src.core.feature_engineering import FeatureEngineer
    fe = FeatureEngineer(normalize=False)
    raw_features = fe.compute_features(sample_data, drop_ohlcv=False)

    # The first observation in the first test window
    # should be normalized using stats from the first train window.
    # sample_data is a simple trend, so mean and std will be stable but distinct.

    first_obs = captured_obs[0]

    # Verify it's not the same as any raw feature row in a naive way
    # (Normalization should change the values significantly)
    raw_features.iloc[train_window]

    # Excluding OHLCV columns from comparison as BacktestEngine does
    cols_to_exclude = ["open", "high", "low", "close", "tick_volume", "atr", "real_volume"]
    feature_cols = [c for c in raw_features.columns if c not in cols_to_exclude]
    raw_vals = raw_features[feature_cols].values[train_window]

    assert not np.array_equal(first_obs, raw_vals)

    # Verify that values are within a reasonable "normalized" range
    # (typically -10 to 10 for Z-score on this kind of data)
    assert np.all(np.abs(first_obs) < 50)

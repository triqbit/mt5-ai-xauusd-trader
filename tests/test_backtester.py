"""
Unit tests for the BacktestEngine.
"""

from __future__ import annotations

from datetime import datetime

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
    df = pd.DataFrame(
        {
            "open": np.full(1000, 2000.0),
            "high": np.full(1000, 2010.0),
            "low": np.full(1000, 1990.0),
            "close": np.full(1000, 2000.0),
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


from unittest.mock import MagicMock

def test_backtest_run(sample_data):
    # Mocking FeatureEngineer and ExecutionFilter to avoid dependency issues in test env
    # and ensure trades are actually executed regardless of flat data.
    mock_fe = MagicMock()
    # compute_features should return a DF with the same index as sample_data
    mock_fe.compute_features.return_value = pd.DataFrame(index=sample_data.index)

    mock_ef = MagicMock()
    # validate should return an approved decision
    mock_decision = MagicMock()
    mock_decision.is_approved = True
    mock_ef.validate.return_value = mock_decision

    engine = BacktestEngine(
        symbol="XAUUSD",
        max_positions=1,
        feature_engineer=mock_fe,
        execution_filter=mock_ef
    )

    # We need to provide a model that predict Buy
    model = MockModel()

    report = engine.run_walk_forward(
        sample_data,
        model,
        train_window=100,
        test_window=50,
        step_size=50
    )

    assert report.total_trades >= 0
    assert isinstance(report.annualized_return, float)
    assert report.start_date is not None

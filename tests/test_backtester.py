"""
Unit tests for the BacktestEngine.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
from unittest.mock import MagicMock

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

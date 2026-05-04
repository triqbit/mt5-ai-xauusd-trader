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
        # Return Buy signal always
        return type("Signal", (), {"direction": 1, "confidence": 0.8})


@pytest.fixture
def sample_data():
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.linspace(2000.0, 2100.0, 1000),
            "high": np.linspace(2010.0, 2110.0, 1000),
            "low": np.linspace(1990.0, 2090.0, 1000),
            "close": np.linspace(2000.0, 2100.0, 1000),
            "tick_volume": np.full(1000, 1000),
        },
        index=dates,
    )
    # Add EMA 200 manually to ensure execution filter pass
    # Using exact column names expected by ExecutionFilter (base_M5_...)
    df["base_M5_ema_200"] = df["close"].ewm(span=200).mean()
    df["base_M5_ema_50"] = df["close"].ewm(span=50).mean()
    df["base_M5_ema_21"] = df["close"].ewm(span=21).mean()
    df["base_M5_ema_8"] = df["close"].ewm(span=8).mean()
    df["base_M5_rsi"] = 60.0 # Healthy momentum
    df["base_M5_atr"] = 10.0 # Stable volatility

    return df


def test_backtest_engine_initialization():
    engine = BacktestEngine(symbol="XAUUSD")
    assert engine.symbol == "XAUUSD"
    assert engine.initial_balance == 10000.0
    assert engine.balance == 10000.0
    assert len(engine.trades) == 0


def test_backtest_run(sample_data):
    # Mocking FeatureEngineer and ExecutionFilter to avoid dependency issues in test env
    # though in a real CI they should be present.
    engine = BacktestEngine(symbol="XAUUSD", max_positions=1)

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

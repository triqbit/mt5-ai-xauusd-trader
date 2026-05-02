"""
Tests for BacktestEngine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.trading.backtester import BacktestEngine
from src.core.config import TradingConfig
from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter
from src.models.base_model import BaseModel, Signal

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.symbol = "XAUUSD"
    config.algorithm = "ensemble"
    config.confidence_threshold = 0.6
    return config

@pytest.fixture
def mock_fe():
    fe = MagicMock(spec=FeatureEngineer)
    # Return a dataframe with one row of features for any input
    fe.compute_features.side_effect = lambda df: pd.DataFrame(
        np.zeros((len(df), 140)), index=df.index, columns=[f"f{i}" for i in range(140)]
    ).iloc[300:] # Simulate dropna for lookback
    return fe

@pytest.fixture
def mock_ef():
    ef = MagicMock(spec=ExecutionFilter)
    return ef

@pytest.fixture
def mock_model():
    model = MagicMock(spec=BaseModel)
    model.predict.return_value = Signal(direction=1, confidence=0.8)
    return model

@pytest.fixture
def sample_data():
    dates = pd.date_range(start="2023-01-01", periods=3000, freq="5min")
    data = pd.DataFrame({
        "open": np.random.randn(3000) + 2000,
        "high": np.random.randn(3000) + 2005,
        "low": np.random.randn(3000) + 1995,
        "close": np.random.randn(3000) + 2000,
        "tick_volume": np.random.randint(100, 1000, 3000)
    }, index=dates)
    return data

def test_vectorized_execution_filter(mock_config, mock_fe, mock_ef, sample_data):
    engine = BacktestEngine(mock_config, mock_fe, mock_ef)
    test_data = sample_data.iloc[:100]
    predictions = pd.Series(1, index=test_data.index)
    confidences = pd.Series(0.8, index=test_data.index)

    # Force some low confidence
    confidences.iloc[0] = 0.5

    # Force some weekend/session block (Mon 2023-01-02 is weekday, Sun 2023-01-01 is weekend)
    # 2023-01-01 00:00 is Sunday.

    approved = engine._vectorized_execution_filter(test_data, predictions, confidences)

    assert approved.iloc[0] == 0 # blocked by confidence

    # Sunday before 17:00 should be blocked
    sunday_index = test_data.index[test_data.index.hour < 17]
    assert (approved.loc[sunday_index] == 0).all()

def test_simulation_transaction_costs(mock_config, mock_fe, mock_ef, sample_data):
    engine = BacktestEngine(mock_config, mock_fe, mock_ef, spread=2.0, commission=5.0)

    test_data = sample_data.iloc[1000:1100]
    signals = pd.Series(0, index=test_data.index)
    signals.iloc[0] = 1 # BUY at the first bar of test_data

    # Set exit price
    entry_time = test_data.index[0]
    exit_time = test_data.index[12]
    test_data.loc[entry_time, "close"] = 2000.0
    test_data.loc[exit_time, "close"] = 2010.0

    trades = engine._vectorized_simulation(test_data, signals)

    assert len(trades) == 1
    trade = trades.iloc[0]

    # raw_pnl = 2010 - 2000 = 10.0
    # cost = 2.0 + 0.05 = 2.05
    # net_pnl = 7.95
    assert pytest.approx(trade["pnl"]) == 7.95

def test_run_walk_forward_full(mock_config, mock_fe, mock_ef, mock_model, sample_data):
    engine = BacktestEngine(mock_config, mock_fe, mock_ef)
    report = engine.run_walk_forward(sample_data, mock_model, train_window_bars=2000, test_window_bars=500)

    assert report.total_trades > 0
    assert report.starting_balance == 10000.0
    assert isinstance(report.sharpe_ratio, float)

"""
Tests for BacktestEngine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.trading.backtester import BacktestEngine, PerformanceReport
from src.core.config import TradingConfig
from src.core.feature_engineering import FeatureEngineer
from src.trading.execution_filter import ExecutionFilter, ExecutionDecision
from src.models.base_model import Signal

@pytest.fixture
def mock_model():
    model = MagicMock()
    # Alternate between Buy and Hold
    def side_effect(obs):
        # Deterministic based on some feature if we wanted, but let's keep it simple
        # For test, return BUY if first feature > 0.5, else HOLD
        if obs[0] > 0.5:
            return Signal(direction=1, confidence=0.8, metadata={})
        return Signal(direction=0, confidence=0.0, metadata={})
    model.predict.side_effect = side_effect
    return model

@pytest.fixture
def mock_fe():
    fe = MagicMock()
    # Mock compute_features to return a DF with one column
    def side_effect(df):
        features = pd.DataFrame(index=df.index)
        # Create a signal-triggering feature
        features['feat1'] = np.where(np.arange(len(df)) % 10 == 0, 0.6, 0.4)
        return features
    fe.compute_features.side_effect = side_effect
    return fe

@pytest.fixture
def mock_filter():
    f = MagicMock()
    f.validate.return_value = ExecutionDecision(None, True, 0.8)
    return f

@pytest.fixture
def config():
    return MagicMock(spec=TradingConfig, symbol="XAUUSD", algorithm="test", timeframe="M5")

@pytest.fixture
def synthetic_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="5min")
    df = pd.DataFrame({
        "open": np.linspace(2000, 2010, 100),
        "high": np.linspace(2002, 2012, 100),
        "low": np.linspace(1998, 2008, 100),
        "close": np.linspace(2000, 2010, 100),
        "tick_volume": 100
    }, index=dates)
    return df

def test_backtest_report_generation(mock_model, mock_fe, mock_filter, config, synthetic_data):
    engine = BacktestEngine(mock_model, mock_fe, mock_filter, config, initial_balance=10000.0)

    # We'll run a single window manually or via run_walk_forward
    # Using run_walk_forward with small window
    report = engine.run_walk_forward(synthetic_data, train_size=20, test_size=20, step_size=20)

    assert isinstance(report, PerformanceReport)
    assert report.total_trades > 0
    assert hasattr(report, "annualized_return")
    assert hasattr(report, "sharpe_ratio")
    assert hasattr(report, "max_drawdown")
    assert hasattr(report, "profit_factor")
    assert hasattr(report, "mae_avg")
    assert hasattr(report, "mfe_avg")

def test_trade_simulation_logic(mock_model, mock_fe, mock_filter, config, synthetic_data):
    engine = BacktestEngine(mock_model, mock_fe, mock_filter, config, spread=0.1, commission_per_lot=5.0)

    # Manually trigger a window
    trades = engine._backtest_window(synthetic_data.iloc[20:40], full_df_for_context=synthetic_data)

    assert len(trades) > 0
    for trade in trades:
        # Check that entry price includes spread (direction * spread/2)
        # For BUY: entry = close + 0.05
        # Close at 20 is around 2002
        assert trade.entry_price > synthetic_data.loc[trade.entry_time, 'close']
        # Check that PnL is calculated (including commission)
        # 1 lot = 100 oz. PnL = (exit-entry)*100 - 5.0
        expected_raw = (trade.exit_price - trade.entry_price) * trade.direction
        expected_pnl = (expected_raw * 100) - 5.0
        assert pytest.approx(trade.pnl, 0.01) == expected_pnl
        # Check MAE/MFE
        assert trade.mae >= 0
        assert trade.mfe >= 0

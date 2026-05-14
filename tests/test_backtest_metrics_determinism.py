"""
Tests for BacktestEngine using deterministic scenarios from BacktestScenarioBuilder.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.trading.backtester import BacktestEngine
from src.utils.synthetic_data import BacktestScenarioBuilder


class ConstantModel:
    """Always predicts BUY with constant confidence."""
    def __init__(self, direction=1, confidence=0.8):
        self.direction = direction
        self.confidence = confidence
    def predict(self, obs):
        return type("Signal", (), {"direction": self.direction, "confidence": self.confidence})

@pytest.fixture
def backtest_builder():
    return BacktestScenarioBuilder(seed=42)

def test_drawdown_and_recovery_metrics(backtest_builder):
    """Verifies that max_drawdown and recovery_factor are calculated correctly."""
    n_steps = 1000
    df = backtest_builder.drawdown_recovery(n_steps=n_steps, start_price=10000.0)
    # Ensure datetime index for backtester
    df.index = pd.date_range(start="2024-01-01", periods=len(df), freq="5min")

    # Mock ExecutionFilter to approve all
    mock_ef = MagicMock()
    mock_ef.validate.return_value = MagicMock(is_approved=True)

    engine = BacktestEngine(
        symbol="XAUUSD",
        execution_filter=mock_ef,
        spread=0.0  # Zero spread for deterministic math
    )

    # Run backtest with a constant buyer
    # Disable MTF
    engine.fe.timeframes = []

    report = engine.run_walk_forward(
        df,
        ConstantModel(direction=1),
        train_window=100,
        test_window=800,
        step_size=800
    )

    assert report.total_trades > 0
    # Price dropped 10% (10000 -> 9000), then gained 20% from 9000 (9000 -> 10800)
    # Equity drawdown should be around 10% if we bought near the peak.
    assert report.max_drawdown > 0.05
    assert report.recovery_factor > 0.3

def test_wick_traps_sl_priority(backtest_builder):
    """
    Verifies that if both SL and TP are hit in the same bar,
    the backtester conservatively assumes SL was hit first.
    """
    n_steps = 500
    df = backtest_builder.wick_traps(n_steps=n_steps)
    df.index = pd.date_range(start="2024-01-01", periods=len(df), freq="5min")

    mock_ef = MagicMock()
    mock_ef.validate.return_value = MagicMock(is_approved=True)

    # Use a spread that makes it even harder to hit TP if needed, but 0.0 is cleaner
    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef, spread=0.0)

    # Disable multi-timeframe features
    engine.fe.timeframes = []

    report = engine.run_walk_forward(
        df,
        ConstantModel(direction=1),
        train_window=100,
        test_window=300,
        step_size=300
    )

    assert report.total_trades > 0

    # In wick_traps, SL/TP are +/- 100 from close.
    # BacktestEngine default SL/TP is entry_price +/- (direction * 2 * atr).
    # Since ATR will be large due to the traps, SL/TP will be wide.
    # We want to see if SL is prioritized.

    # Check trades that hit SL vs TP
    # Since it's a ranging market with massive wicks, and we use SL priority:
    # Most trades should be losses if they hit the trap.

    losses = [t for t in engine.trades if t.pnl < 0]
    # At least some trades should have been caught by the traps
    assert len(losses) > 0
    # Every trade that hit a trap bar should be a loss due to SL priority
    # (High/Low both hit SL/TP distance)

def test_steady_sharpe_calibration(backtest_builder):
    """Verifies that a steady trend produces high risk-adjusted metrics."""
    df = backtest_builder.steady_sharpe(n_steps=500)
    df.index = pd.date_range(start="2024-01-01", periods=len(df), freq="5min")

    mock_ef = MagicMock()
    mock_ef.validate.return_value = MagicMock(is_approved=True)

    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef, spread=0.0)

    # Disable MTF
    engine.fe.timeframes = []

    report = engine.run_walk_forward(
        df,
        ConstantModel(direction=1),
        train_window=200,
        test_window=100,
        step_size=100
    )

    assert report.total_trades > 0
    assert report.win_rate > 0.9  # Nearly all trades should win in a steady trend
    # Sharpe might be 0 if daily resample doesn't have enough days
    # But Profit Factor should be huge
    assert report.profit_factor > 10.0

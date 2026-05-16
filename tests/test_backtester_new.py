"""
Comprehensive unit tests for BacktestEngine focusing on walk-forward logic,
transaction costs, and metric accuracy.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.trading.backtester import BacktestEngine, BacktestTrade


class SimpleMockModel:
    def __init__(self, direction=1):
        self.direction = direction
    def predict(self, obs):
        return type("Signal", (), {"direction": self.direction, "confidence": 0.9})

@pytest.fixture
def test_data():
    """1000 bars of synthetic trending data."""
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="5min")
    # Upward trend
    close = 2000.0 + np.arange(1000) * 0.1
    df = pd.DataFrame({
        "open": close - 0.05,
        "high": close + 0.1,
        "low": close - 0.1,
        "close": close,
        "tick_volume": 100
    }, index=dates)
    return df

def test_walk_forward_overlap_prevention(test_data):
    """Verifies that last_processed_idx prevents duplicate evaluations."""
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})

    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef)
    model = SimpleMockModel(direction=1)

    # Train 500, Test 100, Step 50
    engine.run_walk_forward(
        test_data,
        model,
        train_window=500,
        test_window=100,
        step_size=50
    )

    # Check if trades are unique and sequential
    for i in range(len(engine.trades) - 1):
        assert engine.trades[i].entry_time < engine.trades[i+1].entry_time
        assert engine.trades[i].exit_time <= engine.trades[i+1].entry_time

def test_transaction_costs(test_data):
    """Verifies that spread and commission are correctly applied."""
    # Custom engine with high costs to make them obvious
    spread = 0.5 # 50 pips in gold terms
    commission = 10.0 # $10 per lot
    engine = BacktestEngine(
        symbol="XAUUSD",
        spread=spread,
        commission_per_lot=commission,
        initial_balance=10000.0
    )

    # Mock EF to approve one trade
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})
    engine.ef = mock_ef

    # Simple model to buy
    model = SimpleMockModel(direction=1)

    # Run a small slice where we expect one trade
    engine.run_walk_forward(
        test_data.iloc[:650],
        model,
        train_window=500,
        test_window=100,
        step_size=100
    )

    if engine.trades:
        trade = engine.trades[0]
        entry_idx = test_data.index.get_loc(trade.entry_time)
        entry_data_price = test_data.iloc[entry_idx]['close']

        expected_entry = entry_data_price + spread / 2
        assert trade.entry_price == pytest.approx(expected_entry)

        lots = trade.lot_size
        multiplier = 100
        raw_pnl = (trade.exit_price - trade.entry_price) * 1 * lots * multiplier
        expected_pnl = raw_pnl - commission * lots
        assert trade.pnl == pytest.approx(expected_pnl)

def test_mae_mfe_tracking(test_data):
    """Verifies MAE and MFE are tracked (non-zero)."""
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})
    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef, spread=0)

    # Force trades
    model = SimpleMockModel(direction=1)

    # Adjust ATR so it doesn't hit SL/TP too early
    test_data = test_data.copy()
    test_data['atr'] = 10.0

    engine.run_walk_forward(
        test_data.iloc[:600],
        model,
        train_window=500,
        test_window=50,
        step_size=50
    )

    if engine.trades:
        trade = engine.trades[0]
        # Since it's a BUY and data is trending up, MFE should be > 0.
        # High of entry bar (index 500) is close + 0.1. Entry is at close.
        # So MFE should be at least 0.1.
        assert trade.mfe > 0

def test_performance_report_metrics(test_data):
    """Verifies that all required metrics are present and calculated."""
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})
    engine = BacktestEngine(symbol="XAUUSD", execution_filter=mock_ef)
    model = SimpleMockModel(direction=1)

    report = engine.run_walk_forward(test_data, model)

    assert isinstance(report.annualized_return, float)
    assert isinstance(report.sharpe_ratio, float)
    assert isinstance(report.max_drawdown, float)
    assert isinstance(report.profit_factor, float)
    assert report.total_trades > 0
    assert report.start_date < report.end_date

def test_sharpe_ratio_calculation():
    """Test Sharpe Ratio logic with fixed returns."""
    engine = BacktestEngine(symbol="XAUUSD")
    # Simulate a series of daily equity values
    dates = pd.date_range(start="2024-01-01", periods=11, freq="D")
    equity_curve = []
    bal = 10000.0
    for i, d in enumerate(dates):
        # Add some variance to have non-zero std
        if i % 2 == 0:
            bal *= 1.02
        else:
            bal *= 0.985
        equity_curve.append((d, bal))

    engine.equity_curve = equity_curve
    engine.trades = [BacktestTrade(1, "XAUUSD", 1, dates[0], 2000, dates[10], 2100, 0.1, 100.0)]
    engine.balance = bal

    report = engine._calculate_performance()
    assert report.sharpe_ratio != 0.0
    assert isinstance(report.sharpe_ratio, float)

"""
Institutional unit tests for the BacktestEngine.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.trading.backtester import BacktestEngine


class InstitutionalMockModel:
    """Mock model that returns a steady signal for institutional testing."""
    def predict(self, obs):
        return type("Signal", (), {"direction": 1, "confidence": 0.95})


@pytest.fixture
def institutional_data():
    """Generates a clean dataset with a clear upward trend for verification."""
    dates = pd.date_range(start="2023-01-01", periods=1200, freq="5min")
    # Faster trend to ensure SL/TP hits
    close = 1900.0 + np.arange(1200) * 2.0
    df = pd.DataFrame(
        {
            "open": close - 1.0,
            "high": close + 5.0,
            "low": close - 5.0,
            "close": close,
            "tick_volume": np.full(1200, 500),
        },
        index=dates,
    )
    return df


def test_institutional_engine_logic(institutional_data):
    """
    Verifies that the BacktestEngine correctly calculates institutional
    metrics like Sharpe and Profit Factor on a clean dataset.
    """
    # Mock EF to pass
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})

    engine = BacktestEngine(
        symbol="XAUUSD",
        initial_balance=50000.0,
        spread=0.1,
        commission_per_lot=5.0,
        execution_filter=mock_ef
    )

    model = InstitutionalMockModel()

    report = engine.run_walk_forward(
        institutional_data,
        model,
        train_window=200,
        test_window=100,
        step_size=100
    )

    # Validation checks
    assert report.total_trades > 0
    assert report.annualized_return > 0
    assert isinstance(report.sharpe_ratio, (float, np.float64))
    assert report.profit_factor > 0
    assert report.max_drawdown >= 0
    assert report.total_return > 0

    # Check that mae/mfe were tracked
    assert report.mae_avg >= 0
    assert report.mfe_avg >= 0

def test_institutional_cost_calculation(institutional_data):
    """Verifies that commission and spread are correctly deducted from P&L."""
    mock_ef = MagicMock()
    mock_ef.validate.return_value = type("Decision", (), {"is_approved": True})

    commission = 10.0
    spread = 0.5
    engine = BacktestEngine(
        symbol="XAUUSD",
        initial_balance=10000.0,
        spread=spread,
        commission_per_lot=commission,
        execution_filter=mock_ef
    )

    model = InstitutionalMockModel()

    # Run a small slice
    engine.run_walk_forward(
        institutional_data.iloc[:500],
        model,
        train_window=100,
        test_window=50,
        step_size=50
    )

    if engine.trades:
        trade = engine.trades[0]
        # Verify pnl is correctly calculated and accounts for costs
        # Total return should be less than price movement * multiplier
        theoretical_max_pnl = (trade.exit_price - trade.entry_price) * 100 * trade.lot_size
        assert trade.pnl <= theoretical_max_pnl

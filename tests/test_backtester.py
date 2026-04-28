import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.trading.backtester import BacktestEngine, BacktestTrade, PerformanceReport
from src.models.base import BaseModel, Signal

class MockModel(BaseModel):
    def predict(self, features: np.ndarray) -> Signal:
        # Simple signal logic: Buy if first feature > 0, else Sell if first feature < 0
        if features[0] > 0.5:
            return Signal(direction=1, confidence=0.8)
        elif features[0] < -0.5:
            return Signal(direction=-1, confidence=0.8)
        return Signal(direction=0, confidence=0.0)

@pytest.fixture
def sample_data():
    dates = pd.date_range(start="2023-01-01", periods=200, freq="5min")
    data = pd.DataFrame({
        "open": np.linspace(2000, 2010, 200),
        "high": np.linspace(2001, 2011, 200),
        "low": np.linspace(1999, 2009, 200),
        "close": np.linspace(2000, 2010, 200),
        "tick_volume": [100] * 200
    }, index=dates)
    return data

def test_backtester_initialization():
    engine = BacktestEngine(symbol="XAUUSD", initial_balance=10000.0)
    assert engine.symbol == "XAUUSD"
    assert engine.initial_balance == 10000.0

def test_backtester_run(sample_data):
    model = MockModel()
    engine = BacktestEngine(symbol="XAUUSD", initial_balance=10000.0, spread_pips=0, commission_per_lot=0)

    # We need enough data for the ExecutionFilter (30 bars)
    # The MockModel will generate signals based on normalized features.
    # Since we use linspace, features will be deterministic.

    report, trades = engine.run(sample_data, model)

    assert isinstance(report, PerformanceReport)
    assert isinstance(trades, list)
    # Even if no trades are made, it should return a report
    assert report.total_trades == len(trades)

def test_backtester_metrics_calculation():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 31)
    trades = [
        BacktestTrade(101, "XAUUSD", 1, start, start + timedelta(days=1), 2000, 2010, 1000, 0.1, 0, 10),
        BacktestTrade(102, "XAUUSD", -1, start + timedelta(days=2), start + timedelta(days=3), 2010, 2000, 1000, 0.1, 0, 10),
        BacktestTrade(103, "XAUUSD", 1, start + timedelta(days=4), start + timedelta(days=5), 2000, 1990, -1000, 0.1, -10, 0),
    ]
    engine = BacktestEngine()
    report = engine._calculate_metrics(trades, 11000, [10000, 11000, 12000, 11000], start, end)

    assert report.total_trades == 3
    assert report.profit_factor == 2.0  # (1000 + 1000) / 1000
    assert report.win_rate == pytest.approx(66.66, rel=1e-2)
    assert report.max_drawdown > 0
    assert report.annualized_return > 0

def test_backtester_walk_forward(sample_data):
    # Create more data for WF
    dates = pd.date_range(start="2023-01-01", periods=1000, freq="1h")
    data = pd.DataFrame({
        "open": np.random.randn(1000) + 2000,
        "high": np.random.randn(1000) + 2001,
        "low": np.random.randn(1000) + 1999,
        "close": np.random.randn(1000) + 2000,
        "tick_volume": [100] * 1000
    }, index=dates)

    model = MockModel()
    engine = BacktestEngine()
    report, trades = engine.run_walk_forward(data, model, train_window_days=10, test_window_days=5)

    assert isinstance(report, PerformanceReport)
    assert isinstance(trades, list)

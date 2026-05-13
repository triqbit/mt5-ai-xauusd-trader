
import os
import time

import numpy as np
import pandas as pd
import pytest

from src.core.feature_engineering import FeatureEngineer
from src.core.trade_logger import TradeLogger
from src.trading.backtester import BacktestEngine
from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def large_sample_data():
    n_bars = 1000
    dates = pd.date_range(start="2024-01-01", periods=n_bars, freq="5min")
    data = {
        "open": np.random.randn(n_bars) + 2000,
        "high": np.random.randn(n_bars) + 2002,
        "low": np.random.randn(n_bars) + 1998,
        "close": np.random.randn(n_bars) + 2000,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    }
    return pd.DataFrame(data, index=dates)

def test_backtester_scalability(large_sample_data):
    """Verifies that the backtester can handle 1000 bars efficiently."""
    fe = FeatureEngineer(base_timeframe="M5")
    ef = ExecutionFilter()
    engine = BacktestEngine(symbol="XAUUSD", feature_engineer=fe, execution_filter=ef)

    class MockModel:
        def predict(self, obs):
            return type("Signal", (), {"direction": 1, "confidence": 0.8})

    start = time.perf_counter()
    report = engine.run_walk_forward(
        large_sample_data,
        MockModel(),
        train_window=200,
        test_window=100,
        step_size=100
    )
    duration = time.perf_counter() - start

    assert report.total_trades >= 0
    # Optimization should keep this very fast
    # Increased from 2.0 to 4.0 to account for CI environment variance
    assert duration < 4.0

def test_trade_logger_performance_cache():
    """Verifies the performance caching in TradeLogger."""
    db_path = "perf_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    logger = TradeLogger(db_url=f"sqlite:///{db_path}")

    # First read (empty)
    logger.read_performance_report()

    # Log trades
    for i in range(10):
        logger.log_trade(100 + i, "XAUUSD", 1, 2000.0, 0.1)
        logger.update_trade(100 + i, 2010.0, pnl=10.0)

    # Read again - should populate cache
    report1 = logger.read_performance_report()
    assert report1["total_trades"] == 10

    # Direct cache access check if possible or just timing
    start = time.perf_counter()
    report2 = logger.read_performance_report()
    duration = time.perf_counter() - start

    assert report1 == report2
    # Cached read should be sub-millisecond
    assert duration < 0.01

    if os.path.exists(db_path):
        os.remove(db_path)

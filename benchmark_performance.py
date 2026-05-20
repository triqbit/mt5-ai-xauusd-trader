import os
import time

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.core.trade_logger import TradeLogger


def benchmark_feature_engineering():
    print("Benchmarking Feature Engineering...")
    # Create 500 bars of dummy data
    data = {
        "open": np.random.randn(500) + 2000,
        "high": np.random.randn(500) + 2002,
        "low": np.random.randn(500) + 1998,
        "close": np.random.randn(500) + 2000,
        "tick_volume": np.random.randint(100, 1000, 500),
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start="2024-01-01", periods=500, freq="5min")

    fe = FeatureEngineer(base_timeframe="M5")

    start = time.perf_counter()
    for _ in range(10):
        _ = fe.compute_features(df)
    end = time.perf_counter()
    print(f"Average Feature Engineering time: {(end - start) / 10 * 1000:.2f}ms")


def benchmark_trade_logger():
    print("\nBenchmarking TradeLogger Performance Report...")
    db_path = "benchmark_trades.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    logger = TradeLogger(db_url=f"sqlite:///{db_path}")

    # Insert 1000 closed trades
    print("Inserting 1000 trades...")
    for i in range(1000):
        ticket = 10000 + i
        logger.log_trade(ticket, "XAUUSD", 1, 2000.0, 0.1)
        logger.update_trade(ticket, 2010.0, pnl=100.0 if i % 2 == 0 else -80.0)

    start = time.perf_counter()
    for _ in range(20):
        _ = logger.read_performance_report()
    end = time.perf_counter()
    print(f"Average Performance Report time (1000 trades): {(end - start) / 20 * 1000:.2f}ms")

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    benchmark_feature_engineering()
    benchmark_trade_logger()

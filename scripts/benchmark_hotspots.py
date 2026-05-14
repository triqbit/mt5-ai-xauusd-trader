import os
import time

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer
from src.core.trade_logger import TradeLogger


def benchmark_feature_engineering():
    print("\n--- Benchmarking Feature Engineering ---")
    n_bars = 10000
    data = {
        "open": np.random.randn(n_bars) + 2000,
        "high": np.random.randn(n_bars) + 2002,
        "low": np.random.randn(n_bars) + 1998,
        "close": np.random.randn(n_bars) + 2000,
        "tick_volume": np.random.randint(100, 1000, n_bars),
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start="2020-01-01", periods=n_bars, freq="5min")

    print("\nMode: include_volume_profile=True (Default)")
    fe_on = FeatureEngineer(base_timeframe="M5", include_volume_profile=True)
    start = time.perf_counter()
    _ = fe_on.compute_features(df)
    end = time.perf_counter()
    time_on = (end - start) * 1000
    print(f"Time: {time_on:.2f}ms")

    print("\nMode: include_volume_profile=False")
    fe_off = FeatureEngineer(base_timeframe="M5", include_volume_profile=False)
    start = time.perf_counter()
    _ = fe_off.compute_features(df)
    end = time.perf_counter()
    time_off = (end - start) * 1000
    print(f"Time: {time_off:.2f}ms")

    print(f"\nImprovement: {((time_on - time_off) / time_on) * 100:.1f}%")


def benchmark_trade_logger():
    print("\n--- Benchmarking TradeLogger Performance Report ---")
    db_path = "benchmark_hotspots.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    logger = TradeLogger(db_url=f"sqlite:///{db_path}")

    n_trades = 5000
    print(f"Inserting {n_trades} trades...")
    with logger.Session() as session:
        from src.core.trade_logger import Trade

        for i in range(n_trades):
            ticket = 20000 + i
            trade = Trade(
                ticket=ticket,
                symbol="XAUUSD",
                direction=1 if i % 2 == 0 else -1,
                entry_price=2000.0,
                lot_size=0.1,
                pnl=np.random.uniform(-100, 150),
                status="CLOSED",
            )
            session.add(trade)
        session.commit()

    print("\nMeasuring Report Latency (instrumented)...")
    durations = []
    iters = 5
    for _i in range(iters):
        # Invalidate cache for accurate DB measurement
        logger._perf_cache = None

        start = time.perf_counter()
        _ = logger.read_performance_report()
        end = time.perf_counter()
        durations.append((end - start) * 1000)

    avg_time = sum(durations) / iters
    print(
        f"Average Performance Report time ({n_trades} trades, cache invalidated): {avg_time:.2f}ms"
    )

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    benchmark_feature_engineering()
    benchmark_trade_logger()

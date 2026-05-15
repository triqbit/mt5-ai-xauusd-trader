
import time
import pandas as pd
import numpy as np
from src.core.feature_engineering import FeatureEngineer
import os
import structlog

# Disable logging for benchmark
structlog.configure(processors=[lambda _, __, event_dict: event_dict if False else None])

def benchmark_detailed_fe(n_bars=5000):
    print(f"Benchmarking Feature Engineering with {n_bars} bars...")
    data = {
        "open": np.random.randn(n_bars) + 2000,
        "high": np.random.randn(n_bars) + 2002,
        "low": np.random.randn(n_bars) + 1998,
        "close": np.random.randn(n_bars) + 2000,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start="2024-01-01", periods=n_bars, freq="5min")

    fe = FeatureEngineer(base_timeframe="M5")

    # Warm up
    _ = fe.compute_features(df)

    start = time.perf_counter()
    for _ in range(5):
        _ = fe.compute_features(df)
    end = time.perf_counter()
    avg_time = (end - start) / 5 * 1000
    print(f"Average Feature Engineering time: {avg_time:.2f}ms")

if __name__ == "__main__":
    benchmark_detailed_fe(500)
    benchmark_detailed_fe(5000)

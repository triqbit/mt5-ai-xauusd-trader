import time

import numpy as np
import pandas as pd

from src.core.feature_engineering import FeatureEngineer


def generate_dummy_data(n_bars=1000):
    dates = pd.date_range(start="2024-01-01", periods=n_bars, freq="5min")
    df = pd.DataFrame(
        {
            "open": np.random.uniform(2000, 2100, n_bars),
            "high": np.random.uniform(2100, 2200, n_bars),
            "low": np.random.uniform(1900, 2000, n_bars),
            "close": np.random.uniform(2000, 2100, n_bars),
            "tick_volume": np.random.randint(100, 1000, n_bars),
        },
        index=dates,
    )
    return df


def benchmark():
    fe = FeatureEngineer()
    df = generate_dummy_data(2000)

    print(f"Benchmarking compute_features with {len(df)} bars...")

    start = time.perf_counter()
    features = fe.compute_features(df)
    duration = time.perf_counter() - start

    print(f"Duration: {duration:.4f}s")
    print(f"Features shape: {features.shape}")


if __name__ == "__main__":
    benchmark()

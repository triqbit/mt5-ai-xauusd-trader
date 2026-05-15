
import pandas as pd
import numpy as np
import time

def test_pandas_quantile_perf(n=5000, window=30):
    close = np.random.randn(n) + 2000
    s = pd.Series(close)

    start = time.perf_counter()
    q7 = s.rolling(window).quantile(0.7)
    q3 = s.rolling(window).quantile(0.3)
    end = time.perf_counter()
    print(f"Pandas rolling quantile (n={n}, window={window}): {(end-start)*1000:.2f}ms")

def test_numpy_quantile_perf(n=5000, window=30):
    close = np.random.randn(n) + 2000

    # Simple rolling quantile is hard in pure numpy,
    # but we can use a more efficient approach or bottleneck if available.
    # Without bottleneck, we can use stride_tricks.
    from numpy.lib.stride_tricks import sliding_window_view

    start = time.perf_counter()
    windows = sliding_window_view(close, window)
    q7 = np.percentile(windows, 70, axis=1)
    q3 = np.percentile(windows, 30, axis=1)
    end = time.perf_counter()
    print(f"Numpy/sliding_window percentile (n={n}, window={window}): {(end-start)*1000:.2f}ms")

if __name__ == "__main__":
    test_pandas_quantile_perf(500)
    test_numpy_quantile_perf(500)
    test_pandas_quantile_perf(5000)
    test_numpy_quantile_perf(5000)
    test_pandas_quantile_perf(20000)
    test_numpy_quantile_perf(20000)

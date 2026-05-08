
import pandas as pd
import numpy as np
import pytest
from src.models.regime_detector import RegimeDetector, MarketRegime

def test_regime_vectorization_parity():
    """
    Ensure that the vectorized label_history produces identical results
    to the iterative detect() loop.
    """
    n = 500
    data = {
        "open": np.random.randn(n) + 2000,
        "high": np.random.randn(n) + 2002,
        "low": np.random.randn(n) + 1998,
        "close": np.random.randn(n) + 2000,
        "tick_volume": np.random.randint(100, 1000, n)
    }
    df = pd.DataFrame(data)

    detector = RegimeDetector(window=20, long_window=100)

    # 1. Run iterative labeling (calls detect() in a loop)
    df_iterative = detector.label_history(df.copy(), use_vectorized=False)

    # 2. Run vectorized labeling
    df_vectorized = detector.label_history(df.copy(), use_vectorized=True)

    # Compare results after burn-in period
    burn_in = detector.long_window

    # Check regimes
    pd.testing.assert_series_equal(
        df_iterative["regime"].iloc[burn_in:],
        df_vectorized["regime"].iloc[burn_in:],
        obj="regime"
    )

    # Check confidences (with small tolerance for float precision)
    pd.testing.assert_series_equal(
        df_iterative["regime_confidence"].iloc[burn_in:],
        df_vectorized["regime_confidence"].iloc[burn_in:],
        atol=1e-10,
        obj="regime_confidence"
    )

    # Check volatility index (ATR ratio)
    pd.testing.assert_series_equal(
        df_iterative["volatility_index"].iloc[burn_in:],
        df_vectorized["volatility_index"].iloc[burn_in:],
        atol=1e-10,
        obj="volatility_index"
    )

def test_slope_parity():
    """Verify that convolution-based slope matches the iterative linear regression slope."""
    n = 200
    prices = np.random.randn(n) + 2000
    df = pd.DataFrame({"close": prices, "high": prices+1, "low": prices-1})

    detector = RegimeDetector(window=20)
    features = detector._extract_features(df)

    # Calculate expected slope for a few points using the original method
    for i in range(detector.long_window, n):
        subset = prices[i-detector.window+1 : i+1]
        expected_slope = detector._calculate_slope(subset)
        actual_slope = features["slope"].iloc[i]

        assert pytest.approx(actual_slope, abs=1e-10) == expected_slope

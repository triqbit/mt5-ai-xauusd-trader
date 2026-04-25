"""
Unit tests for Feature Engineering module.
"""

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer

@pytest.fixture
def synthetic_xauusd_data():
    """Generate synthetic XAUUSD M1 data for testing."""
    np.random.seed(42)
    n_periods = 2000 # Enough for D1 features if we were doing many days, but for M1-H4 it's plenty

    # Generate a random walk for price
    returns = np.random.normal(0, 0.001, n_periods)
    price = 2000 * (1 + np.cumsum(returns))

    df = pd.DataFrame({
        "open": price + np.random.normal(0, 0.1, n_periods),
        "high": price + 0.5 + np.random.normal(0, 0.1, n_periods),
        "low": price - 0.5 + np.random.normal(0, 0.1, n_periods),
        "close": price,
        "volume": np.random.randint(100, 1000, n_periods)
    }, index=pd.date_range("2024-01-01", periods=n_periods, freq="min"))

    return df

def test_feature_extraction_count(synthetic_xauusd_data):
    """Verify that 140+ features are generated."""
    # Using only 2 timeframes to speed up test and keep it manageable
    fe = FeatureEngineer(timeframes=["M1", "M5"])
    features = fe.extract_features(synthetic_xauusd_data)

    # 81 features per timeframe (4 EMA + 1 RSI + 3 MACD + 1 ATR + 3 BB + 4 Mom + 2 Stoch + 2 Vol + 61 patterns = 81)
    # 81 * 2 = 162
    assert features.shape[1] >= 140
    assert not features.isnull().values.any()

def test_multi_timeframe_resampling(synthetic_xauusd_data):
    """Verify multi-timeframe features are correctly integrated."""
    fe = FeatureEngineer(timeframes=["M1", "H1"])
    features = fe.extract_features(synthetic_xauusd_data)

    # Check if H1 features exist
    h1_cols = [c for c in features.columns if c.startswith("H1_")]
    assert len(h1_cols) > 0
    assert features.shape[1] >= 140

def test_normalization(synthetic_xauusd_data):
    """Verify that features are normalized (mean ~0, std ~1)."""
    fe = FeatureEngineer(timeframes=["M1"])
    features = fe.extract_features(synthetic_xauusd_data)

    # Check normalization (StandardScaler)
    # Some features might be all zeros (e.g. candle patterns not found), so std will be 0
    means = features.mean()
    stds = features.std()

    # For features with variance, mean should be close to 0 and std close to 1
    varied_features = stds[stds > 1e-6].index
    for col in varied_features:
        assert abs(means[col]) < 1e-1
        assert abs(stds[col] - 1.0) < 1e-1

def test_full_cascade(synthetic_xauusd_data):
    """Test with all default timeframes."""
    fe = FeatureEngineer() # Default timeframes: M1, M5, M15, H1, H4, D1
    # D1 requires 1440 minutes at least. We have 2000.
    features = fe.extract_features(synthetic_xauusd_data)

    # 81 features * 6 timeframes = 486 features
    assert features.shape[1] >= 400
    assert not features.isnull().values.any()

def test_no_look_ahead_bias():
    """Verify that higher timeframe features don't use future data."""
    # Create a simple upward trend
    # Need enough data for indicators to be calculated
    # EMA 200 requires at least 200 data points.
    # For H1 EMA 200, we'd need 200 * 60 = 12,000 minutes.
    # Let's use a smaller timeframe like M5 for the test.
    n_periods = 1000 # 1000 minutes
    df = pd.DataFrame({
        "open": np.arange(n_periods, dtype=float),
        "high": np.arange(n_periods, dtype=float) + 1.0,
        "low": np.arange(n_periods, dtype=float) - 1.0,
        "close": np.arange(n_periods, dtype=float),
        "volume": 100.0
    }, index=pd.date_range("2024-01-01", periods=n_periods, freq="min"))

    fe = FeatureEngineer(timeframes=["M1", "M5"])
    features = fe.extract_features(df, fit_scaler=False)

    # Check for any M5 indicator
    m5_cols = [c for c in features.columns if c.startswith("M5_") and "ema_8" in c]
    assert len(m5_cols) > 0
    m5_ema = m5_cols[0]

    # Get values for 5 minutes (one M5 period)
    # Shift(1) means first M5 candle is at index 5-9 in base (if start is 0).
    # But wait, we drop NaNs.
    # M5 EMA 8 needs 8 M5 candles = 40 minutes.
    # Plus shift(1) = 45 minutes.

    # Look at indices 100 to 105
    period_values = features[m5_ema].iloc[100:105]

    # They should all be identical because they all refer to the same previous M5 candle
    assert len(np.unique(period_values)) == 1

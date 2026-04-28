import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer

@pytest.fixture
def synthetic_data():
    """Generate synthetic M1 OHLCV data for XAUUSD."""
    np.random.seed(42)
    # 60,000 minutes of data (~41 days) to ensure enough D1/H4 warmup
    n_periods = 60000
    idx = pd.date_range("2024-01-01", periods=n_periods, freq="min")

    # Random walk for price
    close = 2000 + np.cumsum(np.random.randn(n_periods) * 0.1)
    open_p = close + np.random.randn(n_periods) * 0.05
    high = np.maximum(open_p, close) + np.random.rand(n_periods) * 0.1
    low = np.minimum(open_p, close) - np.random.rand(n_periods) * 0.1
    volume = np.random.randint(100, 1000, size=n_periods).astype(float)

    df = pd.DataFrame({
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=idx)

    return df

def test_feature_count(synthetic_data):
    """Verify that we compute 140+ features."""
    fe = FeatureEngineer(use_zscore=False)
    processed_df = fe.compute_features(synthetic_data)

    # Base columns: open, high, low, close, volume (5)
    # Plus features
    feature_count = len(fe.feature_cols)
    print(f"Total features: {feature_count}")

    assert feature_count >= 140
    assert "m1_rsi" in processed_df.columns
    assert "m5_rsi" in processed_df.columns
    assert "h1_rsi" in processed_df.columns
    assert "pattern_cdl2crows" in processed_df.columns
    assert "vol_obv" in processed_df.columns

def test_normalization(synthetic_data):
    """Verify Z-score normalization (mean ~ 0, std ~ 1)."""
    fe = FeatureEngineer(use_zscore=True)
    processed_df = fe.compute_features(synthetic_data)

    features = processed_df[fe.feature_cols]

    # Check means are close to 0
    np.testing.assert_allclose(features.mean(), 0, atol=1e-7)

    # Check stds are close to 1 (except for constant features like candle patterns if they didn't trigger)
    # We'll check indicators that are likely to vary
    assert np.isclose(features["m1_rsi"].std(), 1.0, atol=1e-2)
    assert np.isclose(features["m1_atr"].std(), 1.0, atol=1e-2)

def test_lookahead_bias(synthetic_data):
    """Verify no look-ahead bias in multi-timeframe features."""
    fe = FeatureEngineer(use_zscore=False)

    # Compute features on full data
    full_df = fe.compute_features(synthetic_data)

    # Pick a point far enough to have features
    # split_idx should be less than total 60000
    split_idx = 50000
    cut_data = synthetic_data.iloc[:split_idx]

    # Compute features on cut data
    cut_df = fe.compute_features(cut_data)

    assert not cut_df.empty, "Cut data should not result in empty features"

    # Compare the last common row
    common_time = cut_df.index[-1]

    for col in fe.feature_cols:
        # m5, h1 etc should match exactly
        assert np.isclose(full_df.loc[common_time, col], cut_df.loc[common_time, col], atol=1e-7), f"Look-ahead detected in {col}"

def test_nan_handling(synthetic_data):
    """Ensure no NaNs or Infs in the output."""
    fe = FeatureEngineer(use_zscore=True)
    processed_df = fe.compute_features(synthetic_data)

    assert not processed_df.isnull().values.any()
    assert not np.isinf(processed_df.values).any()
    # Ensure we still have enough data after dropping warmup NaNs
    # With 60k rows, and reduced EMA 200 on high TF, we should have plenty of data
    assert len(processed_df) > 5000

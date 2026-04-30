import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def synthetic_xauusd_data():
    """Generate 5000 rows of synthetic XAUUSD M5 data."""
    np.random.seed(42)
    rows = 5000
    start_time = datetime(2023, 1, 1)

    # Generate OHLCV
    close = 1900.0 + np.cumsum(np.random.randn(rows) * 0.5)
    open_p = close + np.random.randn(rows) * 0.1
    high = np.maximum(open_p, close) + np.abs(np.random.randn(rows) * 0.2)
    low = np.minimum(open_p, close) - np.abs(np.random.randn(rows) * 0.2)
    volume = np.random.randint(100, 1000, size=rows).astype(float)

    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    df.index = [start_time + timedelta(minutes=5 * i) for i in range(rows)]
    return df

from src.core.feature_engineering import FeatureEngineer

def test_feature_engineering_pipeline(synthetic_xauusd_data):
    """Test the full feature engineering pipeline."""
    fe = FeatureEngineer(primary_tf="M5")

    # Extract features with fitting
    features_df = fe.extract_features(synthetic_xauusd_data, fit_scaler=True)

    # 1. Check feature count (should be > 140)
    # Base indicators (RSI, MACD(3), ATR, BB(4), EMA(4), DIST_EMA(4)) = 17
    # MTF (M1, M15, H1, H4, D1) each have ~17 features = 17 * 5 = 85
    # Candle patterns = ~60
    # Volume = 3
    # Total ~ 17 + 85 + 60 + 3 = 165
    print(f"Total features: {len(features_df.columns)}")
    assert len(features_df.columns) >= 140

    # 2. Check for NaNs
    assert not features_df.isnull().any().any(), "Features contain NaNs"

    # 3. Check for infinite values
    assert not np.isinf(features_df.values).any(), "Features contain infinite values"

    # 4. Check normalization (mean should be close to 0, std close to 1)
    # Note: synthetic data might not perfectly match, but should be close
    means = features_df.mean()
    stds = features_df.std()

    # Check a few random columns
    for col in features_df.columns[:10]:
        assert abs(means[col]) < 0.1, f"Mean of {col} is not close to 0: {means[col]}"
        assert abs(stds[col] - 1.0) < 0.2 or abs(stds[col]) < 1e-6, f"Std of {col} is not close to 1: {stds[col]}"

def test_mtf_consistency(synthetic_xauusd_data):
    """Test that MTF features are correctly merged."""
    fe = FeatureEngineer(primary_tf="M5")
    features_df = fe.extract_features(synthetic_xauusd_data)

    # Check if some MTF columns exist
    mtf_prefixes = ["M15_", "H1_", "H4_"]
    for prefix in mtf_prefixes:
        assert any(col.startswith(prefix) for col in features_df.columns)

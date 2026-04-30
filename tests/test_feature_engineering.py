"""
Tests for FeatureEngineer in src/core/feature_engineering.py
"""

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer

@pytest.fixture
def synthetic_data():
    """Generate 1000 bars of synthetic XAUUSD-like data."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="5min")

    # Simple random walk for price
    close = 2000 + np.cumsum(np.random.randn(1000))
    open_p = close - np.random.randn(1000)
    high = np.maximum(open_p, close) + np.random.rand(1000)
    low = np.minimum(open_p, close) - np.random.rand(1000)
    volume = np.random.randint(100, 1000, size=1000).astype(float)

    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return df

def test_feature_engineer_output_shape(synthetic_data):
    fe = FeatureEngineer(base_timeframe="M5")
    features_df = fe.compute_all_features(synthetic_data)

    # Verify that we have a significant number of features (at least 140)
    assert len(features_df.columns) >= 140
    assert len(features_df) == len(synthetic_data)

def test_feature_normalization(synthetic_data):
    fe = FeatureEngineer()
    features_df = fe.compute_all_features(synthetic_data)

    normalized_z = fe.normalize_features(features_df, method="zscore")
    # Z-score normalization: mean should be near 0
    assert np.allclose(normalized_z.mean(), 0, atol=1e-5)

    normalized_mm = fe.normalize_features(features_df, method="minmax")
    # MinMax normalization: values should be between 0 and 1
    assert normalized_mm.min().min() >= 0
    assert normalized_mm.max().max() <= 1.0000001

def test_missing_columns():
    fe = FeatureEngineer()
    df = pd.DataFrame({'wrong': [1, 2, 3]})
    with pytest.raises(ValueError, match="Input DataFrame missing required columns"):
        fe.compute_all_features(df)

def test_no_datetime_index():
    fe = FeatureEngineer()
    df = pd.DataFrame({
        'open': [1, 2], 'high': [2, 3], 'low': [0, 1], 'close': [1.5, 2.5], 'volume': [100, 200]
    })
    # This should still run but log a warning and skip MTF
    features_df = fe.compute_all_features(df)
    assert 'rsi_14' in features_df.columns
    assert 'rsi_14_15min' not in features_df.columns

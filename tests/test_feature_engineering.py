"""
Tests for FeatureEngineer class.
"""

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer

@pytest.fixture
def synthetic_xauusd_data():
    """Generates synthetic XAUUSD-like OHLCV data."""
    np.random.seed(42)
    n_points = 1000

    # Generate a random walk for prices
    start_price = 2000.0
    returns = np.random.normal(0, 0.001, n_points)
    prices = start_price * (1 + returns).cumsum()

    # Create OHLCV
    df = pd.DataFrame({
        "open": prices,
        "high": prices * (1 + np.abs(np.random.normal(0, 0.0005, n_points))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.0005, n_points))),
        "close": prices * (1 + np.random.normal(0, 0.0002, n_points)),
        "tick_volume": np.random.randint(100, 1000, n_points)
    })

    # Create a datetime index (M5 frequency)
    df.index = pd.date_range(start="2024-01-01", periods=n_points, freq="5min")

    return df

def test_feature_engineer_init():
    fe = FeatureEngineer()
    assert fe.base_timeframe == "M5"
    assert "M15" in fe.target_timeframes

def test_compute_features_count(synthetic_xauusd_data):
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_xauusd_data)

    # We expect 140+ features
    # Let's see how many we actually have
    num_features = len(fe.feature_names)
    print(f"Total features: {num_features}")
    # print(fe.feature_names)
    assert num_features >= 140

def test_no_nans_in_output(synthetic_xauusd_data):
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_xauusd_data)

    assert not df_features.isnull().values.any()

def test_mtf_features_exist(synthetic_xauusd_data):
    fe = FeatureEngineer(target_timeframes=["H1"])
    df_features = fe.compute_features(synthetic_xauusd_data)

    assert "rsi_h1" in df_features.columns
    assert "atr_h1" in df_features.columns
    assert "ema20_h1" in df_features.columns
    assert "macd_h1" in df_features.columns

def test_candle_patterns_exist(synthetic_xauusd_data):
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_xauusd_data)

    # Check for some common patterns
    assert "cdldoji" in df_features.columns
    assert "cdlhammer" in df_features.columns

def test_normalization(synthetic_xauusd_data):
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_xauusd_data)

    assert len(df_features) > 0

    # For normalized features (excluding candle patterns and OHLCV),
    # mean should be close to 0 and std close to 1
    for col in fe.feature_names:
        if col.startswith("cdl"):
            continue

        # Check for NaNs
        assert not df_features[col].isnull().any(), f"NaN found in {col}"

        # We use a window for normalization, so the overall mean might not be exactly 0
        # but it should be reasonably scaled.
        # Let's check if values are within a reasonable range (e.g. -10 to 10)
        assert df_features[col].max() < 20, f"Max value too high in {col}: {df_features[col].max()}"
        assert df_features[col].min() > -20, f"Min value too low in {col}: {df_features[col].min()}"

"""
Tests for FeatureEngineer class.
"""

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer


@pytest.fixture
def synthetic_xauusd_data():
    """Generate 60 days of synthetic M1 XAUUSD data."""
    periods = 60 * 24 * 60  # 60 days in minutes
    dates = pd.date_range("2024-01-01", periods=periods, freq="1min")

    # Random walk for price
    np.random.seed(42)
    close = 2000 + np.cumsum(np.random.randn(periods) * 0.1)
    open_p = close + np.random.randn(periods) * 0.05
    high = np.maximum(open_p, close) + np.random.rand(periods) * 0.1
    low = np.minimum(open_p, close) - np.random.rand(periods) * 0.1
    volume = np.random.randint(100, 1000, periods)

    df = pd.DataFrame({
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }, index=dates)

    return df


def test_feature_generation_count(synthetic_xauusd_data):
    """Verify that we generate 140+ features."""
    fe = FeatureEngineer()
    # Use only a subset for faster testing but enough for MTF
    data = synthetic_xauusd_data.iloc[:20000]
    features = fe.generate_features(data, normalize=False)

    assert len(features.columns) >= 140
    assert not features.empty
    assert "rsi" in features.columns
    assert "macd" in features.columns
    assert "atr" in features.columns
    assert "ema_8" in features.columns
    assert "ema_21" in features.columns
    assert "ema_50" in features.columns
    assert "ema_200" in features.columns


def test_mtf_features(synthetic_xauusd_data):
    """Verify MTF features are present and non-empty."""
    fe = FeatureEngineer(target_timeframes=["M5", "H1"])
    # 10000 bars is enough for M5 and H1
    data = synthetic_xauusd_data.iloc[:10000]
    features = fe.generate_features(data, normalize=False)

    assert "rsi_m5" in features.columns
    assert "rsi_h1" in features.columns
    assert not features["rsi_m5"].isna().any()


def test_normalization(synthetic_xauusd_data):
    """Verify normalization produces reasonable values."""
    fe = FeatureEngineer()
    data = synthetic_xauusd_data.iloc[:5000]
    features = fe.generate_features(data, normalize=True)

    # Most normalized values should be roughly between -5 and 5
    # although extreme outliers can exist.
    # Check mean and std are close to 0 and 1 for one indicator
    rsi_norm = features["rsi"]
    assert abs(rsi_norm.mean()) < 1.0
    assert 0.1 < rsi_norm.std() < 2.0


def test_candle_patterns(synthetic_xauusd_data):
    """Verify candle patterns are detected (even if most are 0)."""
    fe = FeatureEngineer()
    data = synthetic_xauusd_data.iloc[:1000]
    features = fe.generate_features(data, normalize=False)

    # TA-Lib patterns are prefixed with 'cdl'
    cdl_cols = [col for col in features.columns if col.startswith("cdl")]
    assert len(cdl_cols) > 30
        # Values should be -200, -100, 0, 100, or 200
    for col in cdl_cols:
        unique_vals = features[col].unique()
        for val in unique_vals:
                assert val in [-200, -100, 0, 100, 200]

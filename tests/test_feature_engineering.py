"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_feature_engineering.py
Unit tests for the FeatureEngineer module.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer


@pytest.fixture
def synthetic_ohlcv_data() -> pd.DataFrame:
    """Generate 5000 samples of synthetic XAUUSD-like M1 data."""
    np.random.seed(42)
    n_samples = 5000

    # Brownian motion for price
    returns = np.random.normal(0, 0.0001, n_samples)
    price = 2000 * np.exp(np.cumsum(returns))

    data = {
        "open": price + np.random.normal(0, 0.1, n_samples),
        "high": price + 0.5 + np.random.normal(0, 0.1, n_samples),
        "low": price - 0.5 - np.random.normal(0, 0.1, n_samples),
        "close": price,
        "tick_volume": np.random.randint(100, 1000, n_samples),
    }
    dates = pd.date_range("2024-01-01", periods=n_samples, freq="1min")
    return pd.DataFrame(data, index=dates)


def test_feature_engineering_count(synthetic_ohlcv_data):
    """Test that the engineer produces at least 140 features."""
    fe = FeatureEngineer(use_standard_scaling=False)
    features = fe.compute_features(synthetic_ohlcv_data, base_tf="M1")

    assert not features.empty
    assert features.shape[1] >= 140
    assert len(features) == len(synthetic_ohlcv_data)


def test_feature_engineering_no_nans(synthetic_ohlcv_data):
    """Test that the output has no NaNs (handled by bfill/ffill)."""
    fe = FeatureEngineer(use_standard_scaling=False)
    features = fe.compute_features(synthetic_ohlcv_data, base_tf="M1")

    assert features.isna().sum().sum() == 0


def test_feature_engineering_normalization(synthetic_ohlcv_data):
    """Test that normalization results in near-zero mean and unit variance."""
    fe = FeatureEngineer(use_standard_scaling=True)
    features = fe.compute_features(synthetic_ohlcv_data, base_tf="M1")

    # Select columns that are not constant (StandardScaler might return 0 std for constants)
    # Candle patterns are often constant 0 in synthetic data
    continuous_cols = [c for c in features.columns if ("ema" in c or "rsi" in c) and features[c].std() > 1e-6]

    for col in continuous_cols:
        mean = features[col].mean()
        std = features[col].std()

        assert np.isclose(mean, 0, atol=0.1)
        assert np.isclose(std, 1, atol=0.1)


def test_feature_engineering_mtf_logic(synthetic_ohlcv_data):
    """Test that higher timeframe features are present when base_tf is M1."""
    fe = FeatureEngineer(use_standard_scaling=False)
    features = fe.compute_features(synthetic_ohlcv_data, base_tf="M1")

    # Check for D1 features
    d1_cols = [c for c in features.columns if "_D1" in c]
    assert len(d1_cols) > 0

    # If we set base_tf to D1, we should have NO higher timeframe features
    features_d1 = fe.compute_features(synthetic_ohlcv_data, base_tf="D1")
    mtf_cols = [c for c in features_d1.columns if any(tf in c for tf in ["_M5", "_M15", "_H1", "_H4", "_D1"])]
    assert len(mtf_cols) == 0


def test_empty_dataframe_handling():
    """Test that the engineer handles empty DataFrames gracefully."""
    fe = FeatureEngineer()
    features = fe.compute_features(pd.DataFrame())
    assert features.empty

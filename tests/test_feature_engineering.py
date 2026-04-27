"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_feature_engineering.py
Unit tests for the FeatureEngineer module.
"""

import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer


@pytest.fixture
def xauusd_data() -> pd.DataFrame:
    """Generate synthetic XAUUSD M1 data for 10 days."""
    n_periods = 60 * 24 * 10  # 10 days of M1 data
    np.random.seed(42)

    # Simple random walk for price
    close = 2000 + np.random.randn(n_periods).cumsum()
    open_p = close + np.random.randn(n_periods) * 0.1
    high = np.maximum(open_p, close) + np.random.rand(n_periods) * 0.5
    low = np.minimum(open_p, close) - np.random.rand(n_periods) * 0.5
    volume = np.random.randint(100, 1000, n_periods)

    dates = pd.date_range('2024-01-01', periods=n_periods, freq='1min')
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'tick_volume': volume
    }, index=dates)

    return df


def test_feature_engineer_output_shape(xauusd_data):
    """Test that FeatureEngineer produces the expected number of features."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    # 140+ features requirement
    assert features.shape[1] >= 140
    assert not features.empty
    assert isinstance(features, pd.DataFrame)


def test_feature_normalization(xauusd_data):
    """Test that output features are normalized (approx mean 0, std 1)."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    # Check a few columns for normalization
    for col in features.columns[:10]:
        mean = features[col].mean()
        std = features[col].std()

        assert abs(mean) < 1e-5
        assert abs(std - 1.0) < 1e-5


def test_no_nans_in_output(xauusd_data):
    """Test that the final feature matrix contains no NaNs or Infs."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    assert not features.isnull().any().any()
    assert not np.isinf(features.values).any()


def test_multi_timeframe_consistency(xauusd_data):
    """Test that multi-timeframe features are present."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    expected_tf_prefixes = ["M1_", "M5_", "M15_", "H1_", "H4_", "D1_"]
    for prefix in expected_tf_prefixes:
        assert any(col.startswith(prefix) for col in features.columns)


def test_candle_patterns_present(xauusd_data):
    """Test that TA-Lib candle pattern features are present."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    assert any(col.startswith("Pattern_") for col in features.columns)


def test_volume_features_present(xauusd_data):
    """Test that volume-based features are present."""
    fe = FeatureEngineer(base_timeframe="M1")
    features = fe.extract_features(xauusd_data)

    assert "OBV" in features.columns
    assert "AD" in features.columns
    assert "Rel_Volume" in features.columns


def test_empty_dataframe_handling():
    """Test that the engineer handles empty input gracefully."""
    fe = FeatureEngineer()
    df = pd.DataFrame()
    result = fe.extract_features(df)
    assert result.empty

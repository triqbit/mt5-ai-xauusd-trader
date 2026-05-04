"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_feature_engineering.py
Unit tests for the feature engineering pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from src.core.feature_engineering import FeatureEngineer
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def synthetic_ohlcv():
    """Generate synthetic XAUUSD OHLCV data."""
    gen = ScenarioGenerator(seed=42)
    # 3000 steps of M1 = 600 steps of M5 = 50 steps of H1
    df = gen.generate(n_steps=3000, regime="ranging")
    df.index = pd.date_range(start="2024-01-01", periods=3000, freq="1min")
    return df


def test_feature_engineer_initialization():
    """Test FeatureEngineer constructor."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=True)
    assert fe.base_timeframe == "M1"
    assert fe.normalize is True


def test_compute_features_shape(synthetic_ohlcv):
    """Test the output shape and content of compute_features."""
    # Use smaller periods for MTF to ensure we have data
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    # Should have many features
    assert features.shape[1] > 50
    assert not features.empty

    # Should not contain original OHLCV columns
    for col in ["open", "high", "low", "close", "tick_volume"]:
        assert col not in features.columns


def test_feature_count(synthetic_ohlcv):
    """Test the get_feature_count method."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"])
    fe.compute_features(synthetic_ohlcv)
    assert fe.get_feature_count() == len(fe.feature_columns)


def test_normalization_zscore(synthetic_ohlcv):
    """Test Z-score normalization."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=True, method="zscore")
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    means = features.mean()
    assert np.all(np.abs(means.dropna()) < 1.0)
    # Stds might be 0 for some patterns that never occur, which are replaced by 1 in code
    assert np.all(features.std().dropna() < 2.0)


def test_normalization_minmax(synthetic_ohlcv):
    """Test MinMax normalization."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=True, method="minmax")
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    assert np.all(features.dropna(axis=1) >= -1e-7)
    assert np.all(features.dropna(axis=1) <= 1.0 + 1e-7)


def test_mtf_features(synthetic_ohlcv):
    """Test if MTF features are correctly prefixed and present."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"])
    features = fe.compute_features(synthetic_ohlcv)

    mtf_cols = [col for col in features.columns if "mtf_M5" in col]
    assert len(mtf_cols) > 0


def test_no_look_ahead_bias(synthetic_ohlcv):
    """
    Ensure no look-ahead bias in MTF features.
    """
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)

    df1 = synthetic_ohlcv.copy()
    features1 = fe.compute_features(df1)

    # Change the very last close price in the original data
    df2 = synthetic_ohlcv.copy()
    df2.iloc[-1, df2.columns.get_loc("close")] += 100.0

    fe2 = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features2 = fe2.compute_features(df2)

    # Check a step before the end
    idx = -10
    pd.testing.assert_series_equal(features1.iloc[idx], features2.iloc[idx])


def test_calculate_rolling_slope_correctness():
    """Test mathematical correctness and NaN handling of rolling slope."""
    fe = FeatureEngineer()
    # Simple linear trend: y = 2x + 1
    # indices: 0, 1, 2, 3, 4
    # values:  1, 3, 5, 7, 9
    # slope should be 2.0
    data = pd.Series([1.0, 3.0, 5.0, 7.0, 9.0])
    window = 3

    slope = fe._calculate_rolling_slope(data, window)

    # First window-1 (2) should be NaN
    assert np.isnan(slope.iloc[0])
    assert np.isnan(slope.iloc[1])

    # Subsequent values should be 2.0
    assert np.allclose(slope.iloc[2:], 2.0)


def test_calculate_rolling_slope_short_series():
    """Test handling of series shorter than the window."""
    fe = FeatureEngineer()
    data = pd.Series([1.0, 2.0])
    window = 5
    slope = fe._calculate_rolling_slope(data, window)
    assert np.all(slope == 0.0)


def test_volume_profile_features(synthetic_ohlcv):
    """Test that VWAP and VPT features are computed correctly."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    for period in [20, 50, 100]:
        assert f"vwap_{period}" in features.columns
        assert f"dist_vwap_{period}" in features.columns
        assert not features[f"vwap_{period}"].isna().any()

    assert "vpt" in features.columns
    assert "rvol" in features.columns
    assert not features["vpt"].isna().any()


def test_new_momentum_indicators(synthetic_ohlcv):
    """Test that MFI, CCI, and MOM are present and computed."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert "base_M1_mfi" in features.columns
    assert "base_M1_cci" in features.columns
    assert "base_M1_mom" in features.columns

    assert not features["base_M1_mfi"].isna().any()
    assert not features["base_M1_cci"].isna().any()
    assert not features["base_M1_mom"].isna().any()


def test_full_mtf_suite(synthetic_ohlcv):
    """Test that all requested timeframes generate features."""
    # We need a longer series to have enough D1 data for indicators
    # 1440 mins * 30 days = 43200 steps.
    # For mocking purposes, 3000 is enough if we mock the indicators correctly.
    tfs = ["M1", "M5", "M15", "H1", "H4", "D1"]
    fe = FeatureEngineer(base_timeframe="M5", timeframes=tfs, normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    # M1 and M5 are handled specially (base vs mtf)
    for tf in ["M1", "M15", "H1", "H4", "D1"]:
        mtf_cols = [c for c in features.columns if f"mtf_{tf}" in c]
        assert len(mtf_cols) > 0, f"No features found for {tf}"

    # Explicitly check for 140+ features as requested
    assert fe.get_feature_count() >= 140

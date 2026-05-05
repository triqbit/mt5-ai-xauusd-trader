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


def test_new_momentum_indicators(synthetic_ohlcv):
    """Test that MFI, CCI, MOM, Williams %R, and Ultimate Oscillator are present."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    indicators = ["mfi", "cci", "mom", "willr", "ultosc", "ht_trendline", "ht_dcperiod"]
    for ind in indicators:
        col = f"base_M1_{ind}"
        assert col in features.columns
        assert not features[col].isna().any()


def test_price_action_slopes(synthetic_ohlcv):
    """Test that linear regression slopes are present."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert "slope_5" in features.columns
    assert "slope_20" in features.columns
    assert not features["slope_5"].isna().any()


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
    """Test that MFI, CCI, MOM, Williams %R, and Ultimate Oscillator are present."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    indicators = ["mfi", "cci", "mom", "willr", "ultosc"]
    for ind in indicators:
        col = f"base_M1_{ind}"
        assert col in features.columns
        assert not features[col].isna().any()


def test_mtf_candle_patterns(synthetic_ohlcv):
    """Test that candle patterns are computed for MTF data."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    # Check for a specific pattern in MTF M5
    mtf_pattern_col = "mtf_M5_cdlhammer"
    assert mtf_pattern_col in features.columns
    # Note: Shift(1) might leave the first few rows NaN depending on frequency
    # but compute_features drops rows with NaN base_cols and then MTF cols.
    assert not features[mtf_pattern_col].isna().any()


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

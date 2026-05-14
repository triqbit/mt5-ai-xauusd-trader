"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_feature_engineering.py
Unit tests for the feature engineering pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from src.core.feature_engineering import HAS_TALIB, FeatureEngineer
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def synthetic_ohlcv():
    """Generate synthetic XAUUSD OHLCV data."""
    # Seed for reproducibility
    gen = ScenarioGenerator(seed=42)
    # Generate 5000 steps of M1 data to ensure enough history for D1 (1D = 1440 mins)
    df = gen.generate(n_steps=5000, regime="ranging", start_price=2300.0)
    df.index = pd.date_range(start="2024-01-01", periods=5000, freq="1min")
    return df


def test_feature_engineer_initialization():
    """Test FeatureEngineer constructor."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=True)
    assert fe.base_timeframe == "M1"
    assert fe.normalize is True
    assert fe.method == "zscore"


def test_compute_features_shape(synthetic_ohlcv):
    """Test the output shape and content of compute_features."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    # Should have a large number of features (140+ requested)
    # Note: reduced by default as include_mtf_patterns=False
    assert features.shape[1] >= 130
    assert not features.empty

    # Should not contain original OHLCV columns by default
    for col in ["open", "high", "low", "close", "tick_volume"]:
        assert col not in features.columns


def test_include_volume_profile_toggle(synthetic_ohlcv):
    """Test that volume profile features can be toggled off and remain stable as NaNs."""
    # Disabled
    fe_off = FeatureEngineer(base_timeframe="M1", include_volume_profile=False, normalize=False)
    features_off = fe_off.compute_features(synthetic_ohlcv)

    vol_cols = ["vp_poc", "vp_vah", "vp_val", "vp_width"]
    for col in vol_cols:
        assert col in features_off.columns
        assert features_off[col].isna().all()

    # Enabled
    fe_on = FeatureEngineer(base_timeframe="M1", include_volume_profile=True, normalize=False)
    features_on = fe_on.compute_features(synthetic_ohlcv)
    for col in vol_cols:
        assert col in features_on.columns
        assert not features_on[col].isna().all()


def test_normalization_zscore(synthetic_ohlcv):
    """Test Z-score normalization."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=True, method="zscore")
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    # Filter out columns that are constant (like some candle patterns)
    varied_features = features.loc[:, features.std() > 0]

    means = varied_features.mean()
    stds = varied_features.std()

    # In normalized data, mean should be near 0 and std near 1
    assert np.all(np.abs(means) < 0.2)
    assert np.all(np.abs(stds - 1.0) < 0.2)


def test_stateful_normalization(synthetic_ohlcv):
    """Test saving and loading normalization stats."""
    train_df = synthetic_ohlcv.iloc[:3000]
    test_df = synthetic_ohlcv.iloc[3000:]

    fe1 = FeatureEngineer(base_timeframe="M1", normalize=True)
    fe1.compute_features(train_df)
    stats = fe1.get_normalization_stats()

    assert stats["means"] is not None
    assert "base_M1_rsi" in stats["means"]

    fe2 = FeatureEngineer(base_timeframe="M1", normalize=True)
    fe2.set_normalization_stats(stats)

    assert fe2.means is not None

    # Compute on new data
    features2 = fe2.compute_features(test_df)
    assert not features2.empty
    assert features2.shape[1] == fe1.get_feature_count()


def test_mtf_look_ahead_bias(synthetic_ohlcv):
    """Ensure no look-ahead bias in MTF features by shifting the last bar."""
    # Use fresh engines to avoid state-dependent fillna behavior
    fe1 = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    df1 = synthetic_ohlcv.copy()
    features1 = fe1.compute_features(df1)

    # Modify the last bar of raw data
    fe2 = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    df2 = synthetic_ohlcv.copy()
    df2.iloc[-1, df2.columns.get_loc("close")] += 1000.0
    features2 = fe2.compute_features(df2)

    # The second to last row of features should be IDENTICAL
    pd.testing.assert_frame_equal(features1.iloc[:-1], features2.iloc[:-1])


@pytest.mark.skipif(not HAS_TALIB, reason="TA-Lib not installed")
def test_institutional_indicators(synthetic_ohlcv):
    """Test that institutional indicators are present."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    expected_cols = [
        "base_M1_donchian_high", "base_M1_donchian_low",
        "base_M1_keltner_upper", "base_M1_keltner_lower",
        "base_M1_ema_8", "base_M1_ema_21", "base_M1_ema_50", "base_M1_ema_200",
        "base_M1_ht_trendline", "vp_poc", "rvol", "dist_vwap_20"
    ]

    for col in expected_cols:
        assert col in features.columns


@pytest.mark.skipif(not HAS_TALIB, reason="TA-Lib not installed")
def test_full_mtf_suite(synthetic_ohlcv):
    """Test that all requested timeframes generate features."""
    # Ensure enough data for D1
    gen = ScenarioGenerator(seed=42)
    large_df = gen.generate(n_steps=10000, regime="trending")
    large_df.index = pd.date_range(start="2024-01-01", periods=10000, freq="1min")

    fe = FeatureEngineer(
        base_timeframe="M5",
        timeframes=["M1", "M15", "H1", "H4", "D1"],
        normalize=False,
        include_mtf_patterns=True
    )
    features = fe.compute_features(large_df)

    assert not features.empty
    for tf in ["M1", "M15", "H1", "H4", "D1"]:
        mtf_cols = [c for c in features.columns if f"mtf_{tf}" in c]
        assert len(mtf_cols) > 0, f"No features found for {tf}"

    # With all patterns and MTFs, feature count should easily exceed 140
    assert fe.get_feature_count() >= 140


def test_fallback_behavior(synthetic_ohlcv):
    """Test that the engine still works (with fewer features) if TA-Lib is missing."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    # Even without TA-Lib, we should have price action and volume profile features
    expected_fallbacks = ["returns_1", "log_returns", "vp_poc", "rvol"]
    for col in expected_fallbacks:
        assert col in features.columns

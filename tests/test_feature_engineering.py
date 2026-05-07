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
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    # Should have many features (140+ requested)
    # Base indicators ~ 40, Candle patterns ~ 60, Price action ~ 7, Volume ~ 15
    # MTF M5 ~ 100+
    assert features.shape[1] >= 140
    assert not features.empty

    # Should not contain original OHLCV columns by default
    for col in ["open", "high", "low", "close", "tick_volume"]:
        assert col not in features.columns


def test_normalization_zscore(synthetic_ohlcv):
    """Test Z-score normalization."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=True, method="zscore")
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    # Mocks return zeros, so means will be 0 and std will be replaced by 1.0
    means = features.mean()
    assert np.all(np.abs(means.dropna()) < 1.0)


def test_stateful_normalization(synthetic_ohlcv):
    """Test saving and loading normalization stats."""
    fe1 = FeatureEngineer(base_timeframe="M1", normalize=True, method="zscore")
    fe1.compute_features(synthetic_ohlcv)
    stats = fe1.get_normalization_stats()

    assert stats["means"] is not None
    assert "base_M1_rsi" in stats["means"]

    fe2 = FeatureEngineer(base_timeframe="M1", normalize=True, method="zscore")
    fe2.set_normalization_stats(stats)

    # Check if stats are loaded
    assert fe2.means is not None
    assert fe2.means["base_M1_rsi"] == fe1.means["base_M1_rsi"]

    # Compute with loaded stats
    features2 = fe2.compute_features(synthetic_ohlcv)
    assert not features2.empty


def test_institutional_indicators(synthetic_ohlcv):
    """Test that Donchian, Keltner, and HT features are present."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    # Donchian
    assert "base_M1_donchian_high" in features.columns
    assert "base_M1_donchian_low" in features.columns
    assert "base_M1_donchian_mid" in features.columns

    # Keltner
    assert "base_M1_keltner_upper" in features.columns
    assert "base_M1_keltner_lower" in features.columns

    # Hilbert Transform components
    assert "base_M1_ht_phasor_inphase" in features.columns
    assert "base_M1_ht_sine" in features.columns
    assert "base_M1_ht_trendmode" in features.columns


def test_volume_profile_proxies(synthetic_ohlcv):
    """Test that Volume Profile proxy features are computed."""
    fe = FeatureEngineer(base_timeframe="M1", normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert "vp_poc" in features.columns
    assert "vp_vah" in features.columns
    assert "vp_val" in features.columns
    assert "vp_width" in features.columns


def test_mtf_features(synthetic_ohlcv):
    """Test if MTF features are correctly prefixed and present."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"])
    features = fe.compute_features(synthetic_ohlcv)

    mtf_cols = [col for col in features.columns if "mtf_M5" in col]
    assert len(mtf_cols) > 0


def test_no_look_ahead_bias(synthetic_ohlcv):
    """Ensure no look-ahead bias in MTF features."""
    fe = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)

    df1 = synthetic_ohlcv.copy()
    features1 = fe.compute_features(df1)

    df2 = synthetic_ohlcv.copy()
    # Change the last bar
    df2.iloc[-1, df2.columns.get_loc("close")] += 100.0

    fe2 = FeatureEngineer(base_timeframe="M1", timeframes=["M5"], normalize=False)
    features2 = fe2.compute_features(df2)

    # Check the bar before the last one. It should NOT be affected by the change in the last bar.
    # Note: compute_features drops some rows at the beginning.
    idx = -2
    pd.testing.assert_series_equal(features1.iloc[idx], features2.iloc[idx])


def test_full_mtf_suite(synthetic_ohlcv):
    """Test that all requested timeframes generate features."""
    tfs = ["M1", "M5", "M15", "H1", "H4", "D1"]
    # If base is M5, it should compute MTF for M1, M15, H1, H4, D1
    fe = FeatureEngineer(base_timeframe="M5", timeframes=tfs, normalize=False)
    features = fe.compute_features(synthetic_ohlcv)

    assert not features.empty
    for tf in ["M1", "M15", "H1", "H4", "D1"]:
        mtf_cols = [c for c in features.columns if f"mtf_{tf}" in c]
        assert len(mtf_cols) > 0, f"No features found for {tf}"

    assert fe.get_feature_count() >= 140

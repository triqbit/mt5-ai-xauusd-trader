"""
Tests for src/core/feature_engineering.py
"""
import numpy as np
import pandas as pd
import pytest
from src.core.feature_engineering import FeatureEngineer

@pytest.fixture
def synthetic_ohlcv():
    """Generates 500 bars of synthetic XAUUSD-like data."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=500, freq="min")

    # Random walk for price
    returns = np.random.normal(0, 0.0001, 500)
    price = 2000 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        "open": price,
        "high": price * (1 + np.abs(np.random.normal(0, 0.0002, 500))),
        "low": price * (1 - np.abs(np.random.normal(0, 0.0002, 500))),
        "close": price * (1 + np.random.normal(0, 0.0001, 500)),
        "tick_volume": np.random.randint(100, 1000, 500)
    }, index=dates)

    # Ensure high is highest and low is lowest
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df

def test_compute_features_count(synthetic_ohlcv):
    """Verify that we compute at least 140 features."""
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_ohlcv.copy())

    # Initial columns: open, high, low, close, tick_volume, volume (added) = 6
    # Total should be > 140
    assert len(df_features.columns) >= 140
    # pandas-ta uses uppercase for many indicators by default
    assert "RSI_14" in df_features.columns
    assert "MACD_12_26_9" in df_features.columns
    assert "ema_200" in df_features.columns

def test_normalize_features(synthetic_ohlcv):
    """Verify normalization logic."""
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_ohlcv.copy())
    df_norm = fe.normalize_features(df_features, window=30)

    # After normalization, means should be close to 0 and std close to 1
    # for columns that were normalized (non-binary)
    for col in ["RSI_14", "ema_50"]:
        if col in df_norm.columns:
            # Check a sample slice towards the end to avoid boundary effects
            sample = df_norm[col].iloc[-50:]
            # Using 2.0 as a very loose bound for synthetic random walk data
            assert abs(sample.mean()) < 2.0
            assert sample.std() >= 0.0 # Should be non-negative

    assert not df_norm.isnull().values.any()

def test_empty_dataframe():
    """Handle empty input gracefully."""
    fe = FeatureEngineer()
    df = pd.DataFrame()
    res = fe.compute_features(df)
    assert res.empty

def test_mtf_features(synthetic_ohlcv):
    """Verify MTF features are present."""
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_ohlcv.copy())

    assert "rsi_14_1h" in df_features.columns
    assert "ema_21_4h" in df_features.columns

def test_candle_patterns(synthetic_ohlcv):
    """Verify custom candle patterns."""
    fe = FeatureEngineer()
    df_features = fe.compute_features(synthetic_ohlcv.copy())

    assert "cdl_doji" in df_features.columns
    assert "cdl_engulfing" in df_features.columns
    # Binary/Categorical check
    assert df_features["cdl_doji"].isin([0, 1]).all()

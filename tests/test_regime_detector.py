"""
Unit tests for RegimeDetector.
"""
import numpy as np
import pandas as pd
import pytest
from src.models.regime_detector import RegimeDetector, RegimeType

@pytest.fixture
def detector():
    return RegimeDetector(window_size=10)

def create_synthetic_df(n_bars=200):
    """Base OHLCV data."""
    dates = pd.date_range(start="2023-01-01", periods=n_bars, freq="h")
    df = pd.DataFrame({
        "open": np.ones(n_bars) * 2000.0,
        "high": np.ones(n_bars) * 2005.0,
        "low": np.ones(n_bars) * 1995.0,
        "close": np.ones(n_bars) * 2000.0,
        "volume": np.ones(n_bars) * 1000
    }, index=dates)
    return df

def test_trending_regime(detector):
    df = create_synthetic_df()
    # Create an upward trend
    df["close"] = np.linspace(2000, 2100, len(df))
    df["high"] = df["close"] + 2
    df["low"] = df["close"] - 2

    regime = detector.classify(df)
    # With a steady slope and low volatility, it might be TRENDING or LOW_VOLATILITY_DRIFT
    assert regime.label in [RegimeType.TRENDING, RegimeType.LOW_VOLATILITY_DRIFT]
    assert regime.confidence > 0

def test_news_shock(detector):
    df = create_synthetic_df(n_bars=100)
    # Add a massive spike at the end
    # rel_vol > 3.0 required for NEWS_SHOCK.
    # Current ATR is around 10. We need TR > 30 for rel_vol > 3 (roughly)
    df.loc[df.index[-1], "high"] = 2500.0
    df.loc[df.index[-1], "low"] = 1500.0
    df.loc[df.index[-1], "close"] = 2000.0

    # Also need to make sure historical ATR is small so rel_vol is high
    regime = detector.classify(df)
    print(f"DEBUG: rel_vol={regime.metadata.get('rel_vol')}")
    assert regime.label == RegimeType.NEWS_SHOCK
    assert regime.confidence > 0

def test_ranging_regime(detector):
    df = create_synthetic_df()
    # Flat price
    regime = detector.classify(df)
    assert regime.label == RegimeType.RANGING

def test_historical_labeling(detector):
    df = create_synthetic_df(n_bars=100)
    labeled_df = detector.label_historical(df)

    assert "regime_label" in labeled_df.columns
    assert "regime_confidence" in labeled_df.columns
    assert "transition_score" in labeled_df.columns
    assert len(labeled_df) == len(df)

    # Check that we have some non-unknown labels after the warm-up period
    assert (labeled_df["regime_label"] != RegimeType.UNKNOWN).any()

def test_unsupervised_clustering(detector):
    df = create_synthetic_df()
    clusters = detector.classify_unsupervised(df, n_clusters=3)
    assert len(clusters) == len(df)
    assert clusters.dropna().nunique() <= 3

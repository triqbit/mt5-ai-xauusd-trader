"""
Tests for the RegimeDetector model.
"""
import numpy as np
import pandas as pd
import pytest
from src.models.regime_detector import RegimeDetector, RegimeType, MarketRegime

@pytest.fixture
def base_data():
    """Generate 500 rows of base market data."""
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=500, freq="h")
    data = pd.DataFrame({
        "open": np.random.randn(500).cumsum() + 1900,
        "high": np.random.randn(500).cumsum() + 1905,
        "low": np.random.randn(500).cumsum() + 1895,
        "close": np.random.randn(500).cumsum() + 1900,
        "volume": np.random.randint(100, 1000, 500)
    }, index=dates)
    return data

def test_regime_detector_initialization():
    detector = RegimeDetector()
    assert detector.window_size == 20
    assert detector.volatility_window == 14

def test_detect_unknown_on_short_data():
    detector = RegimeDetector()
    short_df = pd.DataFrame({"close": [1, 2, 3]})
    regime = detector.detect(short_df)
    assert regime.label == RegimeType.UNKNOWN
    assert regime.confidence == 0.0

def test_trending_regime_detection():
    detector = RegimeDetector(window_size=10)
    # Create a very clear trend
    close = np.linspace(1900, 2000, 100) + np.random.normal(0, 0.01, 100)
    df = pd.DataFrame({
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "volume": 100
    })
    # Add some history for ATR and long-term ATR
    history = pd.DataFrame({
        "open": np.random.normal(1900, 1, 100),
        "high": np.random.normal(1902, 1, 100),
        "low": np.random.normal(1898, 1, 100),
        "close": np.random.normal(1900, 1, 100),
        "volume": 100
    })
    full_df = pd.concat([history, df]).reset_index(drop=True)

    regime = detector.detect(full_df)
    assert regime.label == RegimeType.TRENDING
    assert regime.confidence > 0.5

def test_ranging_regime_detection():
    detector = RegimeDetector(window_size=10, trend_threshold=0.5)
    # Create ranging data
    # Constant value
    close = np.full(100, 1900.0)
    df = pd.DataFrame({
        "open": close,
        "high": close + 0.1,
        "low": close - 0.1,
        "close": close,
        "volume": 100
    })
    # Add history for long-term ATR
    history = pd.DataFrame({
        "open": np.random.normal(1900, 1, 100),
        "high": np.random.normal(1902, 1, 100),
        "low": np.random.normal(1898, 1, 100),
        "close": np.random.normal(1900, 1, 100),
        "volume": 100
    })
    full_df = pd.concat([history, df]).reset_index(drop=True)

    regime = detector.detect(full_df)
    assert regime.label == RegimeType.RANGING

def test_volatile_breakout_detection():
    detector = RegimeDetector(window_size=10)
    # History
    history_close = np.random.normal(1900, 1, 100)
    history = pd.DataFrame({
        "open": history_close,
        "high": history_close + 1,
        "low": history_close - 1,
        "close": history_close,
        "volume": 100
    })
    # Volatile Breakout
    breakout_close = np.linspace(1900, 1950, 20)
    breakout = pd.DataFrame({
        "open": breakout_close,
        "high": breakout_close + 10, # High volatility
        "low": breakout_close - 10,
        "close": breakout_close,
        "volume": 1000
    })
    full_df = pd.concat([history, breakout]).reset_index(drop=True)
    regime = detector.detect(full_df)
    assert regime.label in [RegimeType.VOLATILE_BREAKOUT, RegimeType.NEWS_SHOCK]

def test_label_historical(base_data):
    detector = RegimeDetector()
    labeled_df = detector.label_historical(base_data)
    assert "regime" in labeled_df.columns
    assert labeled_df["regime"].nunique() > 0

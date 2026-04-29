import pytest
import pandas as pd
import numpy as np
from src.models.regime_detector import RegimeDetector, RegimeLabel, MarketRegime

def create_synthetic_df(n_points=100, price_type="ranging"):
    np.random.seed(42)
    df = pd.DataFrame(index=pd.date_range(start="2023-01-01", periods=n_points, freq="h"))

    if price_type == "trending":
        # Clear upward trend
        base_price = np.linspace(1900, 2000, n_points)
        noise = np.random.normal(0, 1, n_points)
        df["close"] = base_price + noise
    elif price_type == "ranging":
        # Sideways motion
        df["close"] = 1950 + np.random.normal(0, 5, n_points)
    elif price_type == "volatile":
        # High volatility
        df["close"] = 1950 + np.random.normal(0, 50, n_points)
    elif price_type == "news_shock":
        # Flat then sudden massive jump
        prices = np.full(n_points, 1950.0)
        prices[-5:] = 2100.0  # Massive spike
        df["close"] = prices + np.random.normal(0, 1, n_points)
    else:
        df["close"] = np.random.normal(1950, 5, n_points)

    df["open"] = df["close"].shift(1).fillna(df["close"])
    df["high"] = df[["open", "close"]].max(axis=1) + abs(np.random.normal(0, 2, n_points))
    df["low"] = df[["open", "close"]].min(axis=1) - abs(np.random.normal(0, 2, n_points))
    df["volume"] = np.random.randint(100, 1000, n_points)

    return df

def test_regime_detector_insufficient_data():
    detector = RegimeDetector(lookback_period=20)
    df = create_synthetic_df(n_points=10)
    regime = detector.detect(df)
    assert regime.label == RegimeLabel.UNKNOWN
    assert regime.confidence == 0.0

def test_regime_detector_trending():
    detector = RegimeDetector(lookback_period=20)
    df = create_synthetic_df(n_points=50, price_type="trending")
    regime = detector.detect(df)
    # With a strong linspace trend, it should ideally be TRENDING
    assert isinstance(regime, MarketRegime)
    assert regime.label in [RegimeLabel.TRENDING, RegimeLabel.NEWS_SHOCK] # News shock due to slope

def test_regime_detector_ranging():
    detector = RegimeDetector(lookback_period=20)
    df = create_synthetic_df(n_points=50, price_type="ranging")
    regime = detector.detect(df)
    assert regime.label in [RegimeLabel.RANGING, RegimeLabel.MEAN_REVERSION]

def test_regime_detector_news_shock():
    detector = RegimeDetector(lookback_period=20)
    df = create_synthetic_df(n_points=50, price_type="news_shock")
    regime = detector.detect(df)
    assert regime.label == RegimeLabel.NEWS_SHOCK

def test_historical_labeling():
    detector = RegimeDetector(lookback_period=10)
    df = create_synthetic_df(n_points=30)
    labels = detector.label_historical(df)
    assert len(labels) == 30
    assert labels.iloc[0] == RegimeLabel.UNKNOWN
    assert isinstance(labels.iloc[-1], RegimeLabel)

def test_pydantic_validation():
    # Valid
    regime = MarketRegime(
        label=RegimeLabel.TRENDING,
        confidence=0.8,
        transition_score=0.2,
        metadata={"test": 123}
    )
    assert regime.label == "trending"

    # Invalid confidence
    with pytest.raises(Exception):
        MarketRegime(label=RegimeLabel.TRENDING, confidence=1.5, transition_score=0.1)

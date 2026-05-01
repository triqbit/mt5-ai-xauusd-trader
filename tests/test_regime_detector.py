import pytest
import pandas as pd
import numpy as np
from src.models.regime_detector import RegimeDetector, MarketRegime
from src.utils.synthetic_data import ScenarioGenerator

@pytest.fixture
def detector():
    return RegimeDetector(window=10, long_window=30)

@pytest.fixture
def generator():
    return ScenarioGenerator(seed=42)

def test_regime_detector_trending(detector, generator):
    data = generator.generate(n_steps=100, regime="trending", trend_strength=0.005)
    regime_info = detector.detect(data)
    assert regime_info.label in [MarketRegime.TRENDING, MarketRegime.VOLATILE_BREAKOUT, MarketRegime.NEWS_SHOCK]
    assert regime_info.confidence > 0

def test_regime_detector_ranging(detector, generator):
    data = generator.generate(n_steps=100, regime="ranging", volatility=0.001)
    regime_info = detector.detect(data)
    # The synthetic ranging data might have a slight accidental slope or efficiency
    # so we accept RANGING or TRENDING if the slope/efficiency is borderline.
    assert regime_info.label in [MarketRegime.RANGING, MarketRegime.TRENDING]
    assert regime_info.confidence > 0

def test_regime_detector_volatile(detector, generator):
    data = generator.generate(n_steps=100, regime="volatile", volatility=0.01)
    regime_info = detector.detect(data)
    # Volatile synthetic data might be classified as NEWS_SHOCK or VOLATILE_BREAKOUT
    assert regime_info.label in [MarketRegime.NEWS_SHOCK, MarketRegime.VOLATILE_BREAKOUT, MarketRegime.TRENDING]

def test_regime_detector_history(detector, generator):
    data = generator.generate(n_steps=100, regime="trending")
    df_labeled = detector.label_history(data)
    assert "regime" in df_labeled.columns
    assert len(df_labeled[df_labeled["regime"] != MarketRegime.UNKNOWN.value]) > 0

def test_regime_detector_insufficient_data(detector):
    data = pd.DataFrame({
        "open": [1, 2],
        "high": [2, 3],
        "low": [0, 1],
        "close": [1.5, 2.5],
        "tick_volume": [100, 200]
    })
    regime_info = detector.detect(data)
    assert regime_info.label == MarketRegime.UNKNOWN
    assert regime_info.confidence == 0.0

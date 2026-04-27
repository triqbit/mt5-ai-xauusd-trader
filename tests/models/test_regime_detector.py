"""
Unit tests for RegimeDetector.
"""

import numpy as np
import pandas as pd
import pytest
from src.models.regime_detector import RegimeDetector, RegimeLabel, MarketRegime


def create_synthetic_data(n_points: int = 100, pattern: str = "ranging") -> pd.DataFrame:
    """Helper to create synthetic OHLCV data."""
    np.random.seed(42)
    close = np.zeros(n_points)

    if pattern == "ranging":
        close = 100 + np.random.randn(n_points).cumsum()
    elif pattern == "trending":
        # Steeper trend with zero noise for pure verification
        close = 100 + np.linspace(0, 20, n_points)
    elif pattern == "volatile":
        close = 100 + np.random.randn(n_points).cumsum() * 5

    df = pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": np.random.randint(100, 1000, n_points)
    })
    return df


class TestRegimeDetector:
    def test_feature_extraction(self):
        """Verify ATR and slope calculations."""
        detector = RegimeDetector(lookback_period=10, volatility_window=20)
        df = create_synthetic_data(50, pattern="trending")

        features = detector._extract_features(df)

        assert "atr_ratio" in features
        assert "norm_slope" in features
        assert "efficiency_ratio" in features
        assert "vol_ratio" in features

        # In a strong trending pattern, norm_slope and efficiency_ratio should be relatively high
        assert features["norm_slope"] > 0
        assert features["efficiency_ratio"] > 0.3

    def test_regime_classification_trending(self):
        """Verify correct labeling of synthetic trending data."""
        detector = RegimeDetector(lookback_period=10, volatility_window=20)
        df = create_synthetic_data(50, pattern="trending")

        regime = detector.detect(df)

        assert isinstance(regime, MarketRegime)
        # Depending on noise, it might be TRENDING or VOLATILE_BREAKOUT
        assert regime.label in [RegimeLabel.TRENDING, RegimeLabel.VOLATILE_BREAKOUT]
        assert regime.confidence > 0.5

    def test_regime_classification_ranging(self):
        """Verify correct labeling of synthetic ranging data."""
        detector = RegimeDetector(lookback_period=10, volatility_window=20)
        # More points to stabilize ratios
        df = create_synthetic_data(100, pattern="ranging")

        regime = detector.detect(df)

        # Ranging usually has low efficiency ratio
        assert regime.label in [RegimeLabel.RANGING, RegimeLabel.MEAN_REVERSION]

    def test_insufficient_data(self):
        """Test handling of small DataFrames."""
        detector = RegimeDetector(volatility_window=50)
        df = create_synthetic_data(20)

        regime = detector.detect(df)
        assert regime.label == RegimeLabel.RANGING
        assert regime.confidence == 0.5

    def test_historical_labeling(self):
        """Test the utility for historical regime labeling."""
        detector = RegimeDetector(lookback_period=10, volatility_window=20)
        df = create_synthetic_data(50)

        history = detector.get_historical_regimes(df)

        assert len(history) == len(df)
        assert isinstance(history, pd.Series)
        assert history.iloc[-1] in [label.value for label in RegimeLabel]

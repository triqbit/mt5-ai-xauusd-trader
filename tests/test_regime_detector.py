import unittest
import pandas as pd
import numpy as np
from src.models.regime_detector import RegimeDetector, MarketRegime


class TestRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = RegimeDetector(window=10, long_window=30)

    def test_ranging_regime(self):
        # Generate ranging data (random noise around a constant mean)
        data = pd.DataFrame(
            {
                "close": 2000.0 + np.random.randn(50) * 0.1,
                "high": 2000.2 + np.random.randn(50) * 0.1,
                "low": 1999.8 + np.random.randn(50) * 0.1,
            }
        )
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.RANGING)

    def test_trending_regime(self):
        # Generate trending data (consistent linear increase)
        close = np.linspace(2000, 2010, 50)
        data = pd.DataFrame({"close": close, "high": close + 0.1, "low": close - 0.1})
        info = self.detector.detect(data)
        self.assertIn(info.label, [MarketRegime.TRENDING, MarketRegime.VOLATILE_BREAKOUT])

    def test_news_shock_regime(self):
        # Generate stable data then a sudden huge spike
        close = np.full(50, 2000.0)
        close[-1] = 2050.0  # Spike
        high = close + 0.1
        low = close - 0.1
        data = pd.DataFrame({"close": close, "high": high, "low": low})
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.NEWS_SHOCK)

    def test_insufficient_data(self):
        data = pd.DataFrame({"close": [1.0, 2.0]})
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.UNKNOWN)


if __name__ == "__main__":
    unittest.main()

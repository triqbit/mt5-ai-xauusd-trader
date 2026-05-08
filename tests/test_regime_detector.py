import unittest
import numpy as np
import pandas as pd
from src.models.regime_detector import MarketRegime, RegimeDetector

class TestRegimeDetector(unittest.TestCase):
    def setUp(self):
        # Using smaller windows to make test data generation easier
        self.detector = RegimeDetector(window=10, long_window=30)

    def test_ranging_regime(self):
        np.random.seed(42)
        # Random noise around a constant price
        data = pd.DataFrame({
            'close': 2000.0 + np.random.randn(50) * 0.1,
            'high': 2000.2 + np.random.randn(50) * 0.1,
            'low': 1999.8 + np.random.randn(50) * 0.1
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.RANGING)

    def test_trending_regime(self):
        # Strong steady trend
        close = np.linspace(2000, 2100, 50)
        data = pd.DataFrame({
            'close': close,
            'high': close + 0.1,
            'low': close - 0.1
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.TRENDING)

    def test_news_shock_regime(self):
        # Extreme volatility and high ER
        # Stable then violent moves
        close = np.full(100, 2000.0)
        # Make a very sharp move in one direction to ensure high ER and high ATR ratio
        close[90:] = np.linspace(2000, 2500, 10)

        high = close + 1.0
        low = close - 1.0
        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        # Need to ensure vov is high. Volatility is zero before 90, then huge.
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.NEWS_SHOCK)

    def test_mean_reversion_regime(self):
        # High deviation (z-score) but low efficiency (oscillating)
        close = np.full(60, 2000.0)
        # Oscillate wildly at the end
        for i in range(50, 60):
            close[i] = 2000 + (20 if i % 2 == 0 else -20)

        # Ensure z-score is high at the very last point
        close[-1] = 2050

        high = close + 1.0
        low = close - 1.0
        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.MEAN_REVERSION)

    def test_low_volatility_drift(self):
        np.random.seed(42)
        # Low volatility but steady drift
        close_normal = 2000.0 + np.cumsum(np.random.randn(50) * 5.0) # High vol initial
        # Very low vol drift at the end
        close_drift = close_normal[-1] + np.linspace(0.1, 2.0, 20)
        close = np.concatenate([close_normal, close_drift])

        # Initial high ATR, then very low ATR
        high = close + np.concatenate([np.full(50, 5.0), np.full(20, 0.05)])
        low = close - np.concatenate([np.full(50, 5.0), np.full(20, 0.05)])

        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.LOW_VOLATILITY_DRIFT)

    def test_label_history(self):
        np.random.seed(42)
        data = pd.DataFrame({
            'close': 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
            'high': 2000.5 + np.cumsum(np.random.randn(100) * 0.1),
            'low': 1999.5 + np.cumsum(np.random.randn(100) * 0.1)
        })

        df_history = self.detector.label_history(data)
        self.assertIn('regime', df_history.columns)
        self.assertTrue((df_history['regime'].iloc[:self.detector.long_window-1] == MarketRegime.UNKNOWN.value).all())
        self.assertNotEqual(df_history['regime'].iloc[self.detector.long_window-1], MarketRegime.UNKNOWN.value)

        idx = 50
        info_detect = self.detector.detect(data.iloc[:idx+1])
        self.assertEqual(df_history['regime'].iloc[idx], info_detect.label.value)
        self.assertAlmostEqual(df_history['regime_confidence'].iloc[idx], info_detect.confidence)

    def test_insufficient_data(self):
        data = pd.DataFrame({'close': [1.0, 2.0], 'high': [1.1, 2.1], 'low': [0.9, 1.9]})
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.UNKNOWN)

    def test_gmm_fit_and_detect(self):
        # Generate multi-regime data
        np.random.seed(42)
        ranging = 2000.0 + np.random.randn(100) * 0.1
        trending = np.linspace(2000, 2100, 100)
        volatile = 2100 + np.random.randn(100) * 5.0

        data = pd.DataFrame({
            'close': np.concatenate([ranging, trending, volatile]),
            'high': np.concatenate([ranging + 0.1, trending + 0.1, volatile + 1.0]),
            'low': np.concatenate([ranging - 0.1, trending - 0.1, volatile - 1.0])
        })

        # Fit GMM
        self.detector.fit(data, n_clusters=3)
        self.assertIsNotNone(self.detector._gmm)
        self.assertTrue(len(self.detector._cluster_to_regime) > 0)

        # Post-fit detect should use GMM
        info_post = self.detector.detect(data.iloc[:50])
        self.assertIn(info_post.label, MarketRegime)
        self.assertGreater(info_post.confidence, 0.0)

    def test_vectorized_label_history(self):
        np.random.seed(42)
        data = pd.DataFrame({
            'close': 2000.0 + np.cumsum(np.random.randn(150) * 0.1),
            'high': 2000.0 + np.cumsum(np.random.randn(150) * 0.1) + 0.1,
            'low': 2000.0 + np.cumsum(np.random.randn(150) * 0.1) - 0.1
        })

        df_vec = self.detector.label_history(data, use_vectorized=True)
        df_iter = self.detector.label_history(data, use_vectorized=False)

        self.assertIn('regime', df_vec.columns)
        self.assertEqual(len(df_vec), len(data))

        # Sample check for consistency at multiple points
        for idx in [80, 100, 140]:
            self.assertEqual(df_vec['regime'].iloc[idx], df_iter['regime'].iloc[idx], f"Mismatch at index {idx}")

    def test_generate_summary(self):
        np.random.seed(42)
        data = pd.DataFrame({
            'close': 2000.0 + np.cumsum(np.random.randn(200) * 0.1),
            'high': 2000.0 + np.cumsum(np.random.randn(200) * 0.1) + 0.1,
            'low': 2000.0 + np.cumsum(np.random.randn(200) * 0.1) - 0.1,
            'returns': np.random.randn(200) * 0.001
        })

        summary = self.detector.generate_summary(data)
        from src.research.reporting import RegimeSection
        self.assertIsInstance(summary, RegimeSection)
        self.assertTrue(len(summary.regimes) > 0)
        self.assertIn("Stability", summary.transition_insights)

if __name__ == '__main__':
    unittest.main()

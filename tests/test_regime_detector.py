import unittest

import numpy as np
import pandas as pd

from src.models.regime_detector import MarketRegime, RegimeDetector


class TestRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = RegimeDetector(window=10, long_window=30)

    def test_ranging_regime(self):
        np.random.seed(42)
        data = pd.DataFrame({
            'close': 2000.0 + np.random.randn(50) * 0.1,
            'high': 2000.2 + np.random.randn(50) * 0.1,
            'low': 1999.8 + np.random.randn(50) * 0.1
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.RANGING)

    def test_trending_regime(self):
        close = np.linspace(2000, 2010, 50)
        data = pd.DataFrame({
            'close': close,
            'high': close + 0.1,
            'low': close - 0.1
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.TRENDING)

    def test_news_shock_regime(self):
        # Extreme spike to trigger NEWS_SHOCK (threshold 3.0)
        close = np.full(100, 2000.0)
        close[-1] = 2200.0
        high = np.full(100, 2000.0)
        high[-1] = 2200.0
        low = np.full(100, 2000.0)
        low[-1] = 2000.0
        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.NEWS_SHOCK)

    def test_mean_reversion_regime(self):
        close = np.full(50, 2000.0)
        close[40:50] = [2000, 2005, 1995, 2005, 1995, 2005, 1995, 2005, 1995, 2015]

        high = close + 0.1
        low = close - 0.1
        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.MEAN_REVERSION)

    def test_low_volatility_drift(self):
        np.random.seed(42)
        close_normal = 2000.0 + np.cumsum(np.random.randn(50) * 5.0)
        close_drift = close_normal[-1] + np.linspace(0.1, 2.0, 20)
        close = np.concatenate([close_normal, close_drift])

        high = close + np.concatenate([np.full(50, 10.0), np.full(20, 0.1)])
        low = close - np.concatenate([np.full(50, 10.0), np.full(20, 0.1)])

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
        trending = np.linspace(2000, 2010, 100)
        volatile = 2010 + np.random.randn(100) * 2.0

        data = pd.DataFrame({
            'close': np.concatenate([ranging, trending, volatile]),
            'high': np.concatenate([ranging + 0.1, trending + 0.1, volatile + 0.5]),
            'low': np.concatenate([ranging - 0.1, trending - 0.1, volatile - 0.5])
        })

        # Initial detect should use heuristics
        self.detector.detect(data.iloc[:50])

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
            'close': 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
            'high': 2000.0 + np.cumsum(np.random.randn(100) * 0.1) + 0.1,
            'low': 2000.0 + np.cumsum(np.random.randn(100) * 0.1) - 0.1
        })

        df_vec = self.detector.label_history(data, use_vectorized=True)
        df_iter = self.detector.label_history(data, use_vectorized=False)

        self.assertIn('regime', df_vec.columns)
        self.assertEqual(len(df_vec), len(data))

        # Sample check for consistency
        idx = 80
        self.assertEqual(df_vec['regime'].iloc[idx], df_iter['regime'].iloc[idx])

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

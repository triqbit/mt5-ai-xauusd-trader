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
        self.detector.window = 10
        self.detector.long_window = 100

        close = np.full(200, 2000.0)
        high = np.full(200, 2000.01)
        low = np.full(200, 2000.0)
        high[-1] = 2100.0 # Spike

        data = pd.DataFrame({
            'close': close,
            'high': high,
            'low': low
        })
        info = self.detector.detect(data)
        self.assertEqual(info.label, MarketRegime.NEWS_SHOCK)

    def test_mean_reversion_regime(self):
        close = np.full(50, 2000.0)
        # Creating a Mean Reversion scenario with high z-score and low efficiency
        close[40:50] = [2000, 2005, 1995, 2005, 1995, 2005, 1995, 2005, 1995, 2025] # 2025 gives high z-score

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
        # Need very low volatility (atr_ratio < 0.8) and persistent slope (> 0.00004)
        close_normal = 2000.0 + np.cumsum(np.random.randn(50) * 10.0) # High vol first 50
        close_drift = close_normal[-1] + np.linspace(0.1, 2.0, 20) # Low vol drift next 20
        close = np.concatenate([close_normal, close_drift])

        high = close + np.concatenate([np.full(50, 15.0), np.full(20, 0.05)])
        low = close - np.concatenate([np.full(50, 15.0), np.full(20, 0.05)])

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

    def test_vectorized_features(self):
        np.random.seed(42)
        data = pd.DataFrame({
            'close': 2000.0 + np.cumsum(np.random.randn(100) * 0.1),
            'high': 2000.5 + np.cumsum(np.random.randn(100) * 0.1),
            'low': 1999.5 + np.cumsum(np.random.randn(100) * 0.1)
        })
        feats = self.detector._calculate_features_df(data)
        self.assertIn('atr_ratio', feats.columns)
        self.assertIn('er', feats.columns)
        self.assertIn('slope', feats.columns)
        self.assertIn('z_score', feats.columns)
        self.assertIn('vc', feats.columns)
        self.assertEqual(len(feats), 100)
        # Check some values
        self.assertTrue(np.isnan(feats['atr_ratio'].iloc[0]))
        self.assertFalse(np.isnan(feats['atr_ratio'].iloc[30]))

    def test_clustering_gmm(self):
        self.detector.use_clustering = True
        np.random.seed(42)
        # Mix of ranging and trending to fit
        data_ranging = pd.DataFrame({
            'close': 2000.0 + np.random.randn(100) * 0.1,
            'high': 2000.2 + np.random.randn(100) * 0.1,
            'low': 1999.8 + np.random.randn(100) * 0.1
        })
        data_trending = pd.DataFrame({
            'close': np.linspace(2000, 2010, 100),
            'high': np.linspace(2000, 2010, 100) + 0.1,
            'low': np.linspace(2000, 2010, 100) - 0.1
        })
        data = pd.concat([data_ranging, data_trending], ignore_index=True)

        self.detector.fit(data)
        self.assertIsNotNone(self.detector._gmm)
        self.assertGreater(len(self.detector._cluster_map), 0)

        info = self.detector.detect(data_trending.tail(50))
        self.assertNotEqual(info.label, MarketRegime.UNKNOWN)

        df_history = self.detector.label_history(data)
        self.assertIn('regime', df_history.columns)
        self.assertTrue((df_history['regime'] != MarketRegime.UNKNOWN.value).any())

if __name__ == '__main__':
    unittest.main()

import unittest

import numpy as np
import pandas as pd

from src.models.feature_engineer import FeatureEngineer, PANDAS_TA_AVAILABLE


class TestFeatureEngineer(unittest.TestCase):
    def setUp(self):
        self.fe = FeatureEngineer(include_patterns=False)
        # Create 500 bars of dummy data
        np.random.seed(42)
        self.df = pd.DataFrame({
            "open": np.random.randn(500).cumsum() + 100,
            "high": np.random.randn(500).cumsum() + 102,
            "low": np.random.randn(500).cumsum() + 98,
            "close": np.random.randn(500).cumsum() + 100,
            "tick_volume": np.random.randint(100, 1000, 500)
        })

    def test_generate_features_returns_dataframe(self):
        features_df = self.fe.generate_features(self.df)
        self.assertIsInstance(features_df, pd.DataFrame)
        # Original close column must be preserved
        self.assertIn('close', features_df.columns)

    @unittest.skipUnless(PANDAS_TA_AVAILABLE, "pandas-ta not installed")
    def test_generate_features_adds_indicators(self):
        features_df = self.fe.generate_features(self.df)
        # Check that features were added
        self.assertGreater(len(self.fe.feature_columns), 0)
        # Verify at least one well-known indicator column exists
        # pandas-ta naming: RSI_14, SMA_20, ATRr_14 (atr uses ATRr prefix)
        has_rsi = any('RSI' in col.upper() for col in features_df.columns)
        has_sma = any('SMA' in col.upper() for col in features_df.columns)
        has_atr = any('ATR' in col.upper() for col in features_df.columns)
        self.assertTrue(has_rsi, f"Expected RSI column. Got: {list(features_df.columns)[:20]}")
        self.assertTrue(has_sma, f"Expected SMA column. Got: {list(features_df.columns)[:20]}")
        self.assertTrue(has_atr, f"Expected ATR column. Got: {list(features_df.columns)[:20]}")

    @unittest.skipUnless(PANDAS_TA_AVAILABLE, "pandas-ta not installed")
    def test_normalize_features(self):
        features_df = self.fe.generate_features(self.df)
        if not self.fe.feature_columns:
            self.skipTest("No feature columns generated")
        normalized_df = self.fe.normalize_features(features_df, method="zscore")
        # Select a feature column and check mean/std
        col = self.fe.feature_columns[0]
        # Ignore NaNs for the check
        data = normalized_df[col].dropna()
        self.assertAlmostEqual(data.mean(), 0, places=1)
        self.assertAlmostEqual(data.std(), 1, places=1)

    def test_missing_columns(self):
        df_bad = pd.DataFrame({"close": [1, 2, 3]})
        features_df = self.fe.generate_features(df_bad)
        # Should return original and log error (not crash)
        self.assertEqual(len(features_df.columns), 1)

    def test_normalize_features_empty_returns_unchanged(self):
        # When feature_columns is empty, normalize should return unchanged df
        fe = FeatureEngineer(include_patterns=False)
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
        result = fe.normalize_features(df)
        pd.testing.assert_frame_equal(result, df)


if __name__ == "__main__":
    unittest.main()

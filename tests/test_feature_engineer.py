import unittest
import pandas as pd
import numpy as np
from src.models.feature_engineer import FeatureEngineer

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

    def test_generate_features(self):
        features_df = self.fe.generate_features(self.df)
        # Check that original columns are preserved (possibly renamed/mapped)
        self.assertIn('close', features_df.columns)
        # Check that features were added
        self.assertTrue(len(self.fe.feature_columns) > 0)
        # Check specific indicators
        self.assertIn('RSI_14', features_df.columns)
        self.assertIn('SMA_20', features_df.columns)
        self.assertIn('ATRr_14', features_df.columns)

    def test_normalize_features(self):
        features_df = self.fe.generate_features(self.df)
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

if __name__ == "__main__":
    unittest.main()

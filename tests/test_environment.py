import unittest

import numpy as np
import pandas as pd

from src.environment.gym_env import TradingEnv
from src.models.feature_engineer import FeatureEngineer


class TestTradingEnv(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        # Create 1000 bars to ensure enough data after dropna()
        # Using a more varied signal to avoid constant values which might break some indicators
        price = 100 + np.cumsum(np.random.randn(1000) * 0.1)
        self.df = pd.DataFrame({
            "open": price + np.random.randn(1000) * 0.01,
            "high": price + 0.05,
            "low": price - 0.05,
            "close": price,
            "tick_volume": np.random.randint(100, 1000, 1000)
        })
        # Use a feature engineer with few patterns to speed up
        self.fe = FeatureEngineer(include_patterns=False)
        self.env = TradingEnv(self.df, window_size=10, feature_engineer=self.fe)

    def test_reset(self):
        obs, _info = self.env.reset()
        expected_size = 10 * len(self.env.fe.feature_columns) + 2
        self.assertEqual(len(obs), expected_size)
        self.assertEqual(self.env.balance, 10000.0)
        self.assertEqual(self.env.position, 0)

    def test_step_buy_sell(self):
        self.env.reset()
        # Step with Buy action (1)
        _obs, _reward, _terminated, _truncated, _info = self.env.step(1)
        self.assertEqual(self.env.position, 1.0)
        self.assertGreater(self.env.entry_price, 0)

        # Step with Sell action (2) - closes position
        _obs, _reward, _terminated, _truncated, _info = self.env.step(2)
        self.assertEqual(self.env.position, 0.0)

    def test_termination(self):
        # Ensure enough data for indicators (SMA 200 needs 200 bars) + window
        df_small = self.df.iloc[:300]
        env_small = TradingEnv(df_small, window_size=10, feature_engineer=self.fe)
        env_small.reset()

        terminated = False
        # Move through all available steps
        max_steps = len(env_small.features) - env_small.window_size
        for _ in range(max_steps + 1):
            _obs, _reward, terminated, _truncated, _info = env_small.step(0)
            if terminated:
                break
        self.assertTrue(terminated)

if __name__ == "__main__":
    unittest.main()

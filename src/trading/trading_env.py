"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Custom Gymnasium-compatible environment for XAUUSD trading.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class TradingEnv(gym.Env):
    """
    Custom environment for trading XAUUSD.
    Follows Gymnasium API.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, df=None, window_size=20):
        super().__init__()
        self.df = df
        self.window_size = window_size

        # Actions: 0 = HOLD, 1 = BUY, 2 = SELL
        self.action_space = spaces.Discrete(3)

        # Observation space: Window of features
        # Assuming features are normalized
        num_features = df.shape[1] if df is not None else 140
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(window_size, num_features), dtype=np.float32
        )

        self.current_step = window_size
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = self.window_size
        obs = self._get_observation()
        return obs, {}

    def step(self, action):
        self.current_step += 1

        # Simple placeholder reward: return of the next period if bought, etc.
        reward = 0.0

        done = False
        if self.df is not None and self.current_step >= len(self.df) - 1:
            done = True

        truncated = False
        obs = self._get_observation()

        return obs, reward, done, truncated, {}

    def _get_observation(self):
        if self.df is None:
            return np.zeros(self.observation_space.shape, dtype=np.float32)

        obs = self.df.iloc[self.current_step - self.window_size : self.current_step].values
        return obs.astype(np.float32)

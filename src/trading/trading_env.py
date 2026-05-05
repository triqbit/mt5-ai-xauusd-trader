"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Custom Gymnasium-compatible environment for XAUUSD trading.
"""

import logging
from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces


class TradingEnv(gym.Env):
    """
    Custom environment for trading XAUUSD.
    Follows Gymnasium API.

    Attributes:
        df: DataFrame containing historical market data.
        window_size: Number of past time steps to include in the observation.
        action_space: Gymnasium action space (0=HOLD, 1=BUY, 2=SELL).
        observation_space: Gymnasium observation space (window_size x num_features).
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, df: pd.DataFrame | None = None, window_size: int = 20) -> None:
        """
        Initializes the trading environment.

        Args:
            df: Optional DataFrame containing historical market data.
            window_size: Number of past time steps to include in the observation.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
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

        # Optimization: Pre-convert to numpy array with correct dtype to avoid
        # expensive repeated indexing and casting in _get_observation.
        self._data = df.values.astype(np.float32) if df is not None else None

        self.current_step = window_size
        self.reset()

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Resets the environment to its initial state.

        Args:
            seed: Optional seed for random number generation.
            options: Optional dictionary of options.

        Returns:
            A tuple containing the initial observation and an empty info dictionary.
        """
        super().reset(seed=seed)
        self.current_step = self.window_size
        obs = self._get_observation()
        return obs, {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """
        Executes one step in the environment.

        Args:
            action: The action to take (0=HOLD, 1=BUY, 2=SELL).

        Returns:
            A tuple containing (observation, reward, terminated, truncated, info).
        """
        self.current_step += 1

        # Reward logic - Placeholder skeleton
        # In a production env, this would use realized/unrealized P&L,
        # transaction costs, and potentially risk-adjusted metrics like Sharpe.
        reward = 0.0
        if self._data is not None and self.current_step < len(self._data):
            # Example: Simple price change reward for BUY/SELL
            current_price = self._data[self.current_step, 3]  # Assuming index 3 is Close
            prev_price = self._data[self.current_step - 1, 3]
            price_change = current_price - prev_price

            if action == 1:  # BUY
                reward = float(price_change)
            elif action == 2:  # SELL
                reward = float(-price_change)
            # action == 0 (HOLD) -> reward = 0

        terminated = False
        if self._data is not None and self.current_step >= len(self._data) - 1:
            terminated = True

        truncated = False
        obs = self._get_observation()

        # Add metadata for debugging or monitoring
        info = {
            "step": self.current_step,
            "action": action,
            "reward": reward,
        }

        return obs, reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        Constructs the current observation from the pre-converted NumPy data.

        Returns:
            A numpy array representing the observation window.
        """
        if self._data is None:
            return np.zeros(self.observation_space.shape, dtype=np.float32)

        # Optimization: Direct numpy slicing is ~50x faster than df.iloc[].values.astype()
        return self._data[self.current_step - self.window_size : self.current_step]

    def render(self) -> None:
        """
        Renders the current state of the environment (not implemented).
        """
        pass

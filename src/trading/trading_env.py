"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
XAUUSD-specific Gymnasium trading environment skeleton.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class XAUUSDTradingEnv(gym.Env):
    """
    A specialized Gymnasium environment for XAUUSD (Gold) trading.
    This environment handles the data windowing, reward calculation, and
    trade execution logic for reinforcement learning agents.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        window_size: int = 60,
        initial_balance: float = 10000.0,
        commission: float = 0.0002,
        symbol: str = "XAUUSD",
    ) -> None:
        """
        Initialize the environment.

        Args:
            df: DataFrame containing market data and indicators.
            window_size: Number of past time steps to include in each observation.
            initial_balance: Starting account balance.
            commission: Transaction fee per trade.
            symbol: Trading symbol name.
        """
        super().__init__()
        self.df = df.reset_index(drop=True)
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.commission = commission
        self.symbol = symbol

        # Number of features from the dataframe
        self.n_features = len(df.columns)

        # Observation: window of OHLCV + indicators, plus portfolio state (balance, position)
        # We flatten the window and append portfolio state or use a Dict space.
        # For simplicity with PPO, we use a flattened Box space.
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.window_size * self.n_features + 2,),
            dtype=np.float32,
        )

        # Actions: 0 = Hold, 1 = Buy, 2 = Sell
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the environment to an initial state."""
        super().reset(seed=seed)
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.position = 0.0  # 0: None, 1.0: Long, -1.0: Short
        self.entry_price = 0.0

        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executes one time step within the environment.

        Args:
            action: The action to take (0=Hold, 1=Buy, 2=Sell).

        Returns:
            observation, reward, terminated, truncated, info
        """
        # 1. Update step
        self.current_step += 1

        # 2. Basic termination logic
        terminated = self.current_step >= len(self.df) - 1
        truncated = False

        # 3. Execution logic stub
        # (In a real implementation, this would update balance and position)
        reward = 0.0

        # 4. Get next observation
        observation = self._get_observation()

        info = {"balance": self.balance, "position": self.position, "step": self.current_step}

        return observation, reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """Constructs the observation vector."""
        # Select the window of data
        window = self.df.iloc[self.current_step - self.window_size : self.current_step].values

        # Normalize the window (simple Z-score normalization)
        mean = window.mean(axis=0)
        std = window.std(axis=0) + 1e-8
        normalized_window = (window - mean) / std

        # Flatten and append portfolio state
        portfolio_state = np.array(
            [self.balance / self.initial_balance, self.position], dtype=np.float32
        )

        return np.concatenate([normalized_window.flatten(), portfolio_state]).astype(np.float32)

    def render(self, mode: str = "human") -> None:
        """Renders the environment."""
        print(
            f"Step: {self.current_step} | Balance: {self.balance:.2f} | Position: {self.position}"
        )

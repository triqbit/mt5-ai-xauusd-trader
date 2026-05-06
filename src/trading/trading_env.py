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

    def __init__(
        self,
        df: pd.DataFrame | None = None,
        window_size: int = 20,
        initial_balance: float = 10000.0,
    ) -> None:
        """
        Initializes the trading environment.

        Args:
            df: Optional DataFrame containing historical market data.
            window_size: Number of past time steps to include in the observation.
            initial_balance: Starting account balance.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.df = df
        self.window_size = window_size
        self.initial_balance = initial_balance

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

        # State variables
        self.balance = initial_balance
        self.equity = initial_balance
        self.position = 0  # 0: None, 1: Long, -1: Short (Simplified)
        self.entry_price = 0.0
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
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.position = 0
        self.entry_price = 0.0

        obs = self._get_observation()
        return obs, {"balance": self.balance, "equity": self.equity}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """
        Executes one step in the environment.

        Args:
            action: The action to take (0=HOLD, 1=BUY, 2=SELL).

        Returns:
            A tuple containing (observation, reward, terminated, truncated, info).
        """
        self.current_step += 1

        # In a production env, these would come from config or live data
        spread = 0.0002
        slippage = 0.0001

        reward = 0.0
        if self._data is not None and self.current_step < len(self._data):
            # Assuming index 3 is Close price
            current_price = self._data[self.current_step, 3]
            prev_price = self._data[self.current_step - 1, 3]

            # Update equity based on open position
            if self.position == 1:  # Long
                unrealized_pnl = current_price - prev_price
                self.equity += unrealized_pnl
                reward = float(unrealized_pnl)
            elif self.position == -1:  # Short
                unrealized_pnl = prev_price - current_price
                self.equity += unrealized_pnl
                reward = float(unrealized_pnl)

            # Handle actions (categorical: 0=HOLD, 1=BUY, 2=SELL)
            if action == 1:  # Want to go LONG
                if self.position == -1:  # Close short first
                    realized_pnl = self.entry_price - current_price - (spread + slippage)
                    self.balance += realized_pnl
                    self.position = 0

                if self.position == 0:  # Open long
                    self.position = 1
                    self.entry_price = current_price + (spread + slippage)
                    # Apply immediate cost to equity
                    self.equity -= (spread + slippage)

            elif action == 2:  # Want to go SHORT
                if self.position == 1:  # Close long first
                    realized_pnl = current_price - self.entry_price - (spread + slippage)
                    self.balance += realized_pnl
                    self.position = 0

                if self.position == 0:  # Open short
                    self.position = -1
                    self.entry_price = current_price - (spread + slippage)
                    # Apply immediate cost to equity
                    self.equity -= (spread + slippage)

            elif action == 0:  # HOLD / CLOSE
                # Optional: In some envs, action 0 means "no position"
                # For this skeleton, we'll keep it as "do nothing to current position"
                pass

        terminated = False
        if self._data is not None and self.current_step >= len(self._data) - 1:
            terminated = True
            # Close any open position at the end
            if self.position != 0:
                self.balance = self.equity
                self.position = 0

        truncated = False
        obs = self._get_observation()

        # Add metadata for debugging or monitoring
        info = {
            "step": self.current_step,
            "action": action,
            "reward": reward,
            "balance": float(self.balance),
            "equity": float(self.equity),
            "position": self.position,
            "spread": spread,
            "slippage": slippage,
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

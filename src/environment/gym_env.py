"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/environment/gym_env.py
Custom Gymnasium trading environment for RL training.
"""

from __future__ import annotations

import logging

import gymnasium as gym
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TradingEnv(gym.Env):
    """
    Custom Gymnasium environment for XAUUSD trading.
    State: OHLCV + technical indicators (configurable window)
    Actions: 0=Hold, 1=Buy, 2=Sell
    Reward: Risk-adjusted PnL (normalized)
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        data: np.ndarray,
        initial_balance: float = 10000.0,
        window_size: int = 60,
        commission: float = 0.0002,
    ):
        super().__init__()
        self.data = data.astype(np.float32)
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        n_features = data.shape[1]

        # Pre-calculate rolling statistics for faster observation normalization
        df = pd.DataFrame(self.data)
        self.means = df.rolling(window=window_size).mean().values
        self.stds = df.rolling(window=window_size).std(ddof=0).values

        # Pre-allocate observation buffer
        self.obs_shape = (window_size * n_features + 2,)
        self.obs_buffer = np.empty(self.obs_shape, dtype=np.float32)

        # Observation: window of market data + portfolio state [balance, position]
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=self.obs_shape, dtype=np.float32
        )

        # Actions: 0=Hold, 1=Buy, 2=Sell
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def reset(
        self, seed: int | None = None, options: dict | None = None
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.position = 0.0  # Current position in lots
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0
        self.cumulative_commissions = 0.0
        return self._get_observation(), {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        current_price = self.data[self.current_step, 3]  # Close price
        reward = 0.0

        # Execute action
        if action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            comm_cost = current_price * self.commission
            self.entry_price = current_price + comm_cost
            self.cumulative_commissions += comm_cost
        elif action == 2 and self.position == 1:  # Sell / Close Long
            comm_cost = current_price * self.commission
            pnl = (current_price - comm_cost) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            self.cumulative_commissions += comm_cost
            reward = pnl / self.initial_balance * 100  # Normalized reward
            self.position = 0.0
            self.entry_price = 0.0

        # Unrealized PnL for intermediate steps
        if self.position == 1:
            unrealized = current_price - self.entry_price
            reward += unrealized / self.initial_balance

        self.current_step += 1

        terminated = self.balance <= 0 or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_pnl": self.total_pnl,
            "cumulative_commissions": self.cumulative_commissions,
        }
        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        Optimized observation generation.
        Uses pre-calculated rolling stats and a pre-allocated buffer.
        """
        window = self.data[self.current_step - self.window_size : self.current_step]
        mean = self.means[self.current_step - 1]
        std = self.stds[self.current_step - 1]

        # Vectorized normalization
        obs_normalized = (window - mean) / (std + 1e-8)

        # Populate pre-allocated buffer
        flat_size = self.window_size * self.data.shape[1]
        self.obs_buffer[:flat_size] = obs_normalized.ravel()
        self.obs_buffer[flat_size] = self.balance / self.initial_balance
        self.obs_buffer[flat_size + 1] = self.position

        return self.obs_buffer.copy()

    def render(self):
        """Render the environment state."""
        # Use logging instead of print for enterprise compliance
        logger.info(
            "Step: %d | Balance: $%.2f | Position: %.1f",
            self.current_step,
            self.balance,
            self.position,
        )

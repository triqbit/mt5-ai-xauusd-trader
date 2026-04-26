"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/environment/gym_env.py
Custom Gymnasium trading environment for RL training.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import gymnasium as gym
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False

logger = logging.getLogger(__name__)


class TradingEnvSkeleton:
    """Base skeleton for TradingEnv when gymnasium is not available."""
    metadata = {"render_modes": ["human"]}

    def __init__(self, *args, **kwargs):
        pass

    def reset(self, *args, **kwargs):
        raise NotImplementedError("Gymnasium not installed")

    def step(self, *args, **kwargs):
        raise NotImplementedError("Gymnasium not installed")


BaseEnv = gym.Env if GYM_AVAILABLE else TradingEnvSkeleton


class TradingEnv(BaseEnv):
    """
    Custom Gymnasium environment for XAUUSD trading.
    State: OHLCV + technical indicators (configurable window)
    Actions: 0=Hold, 1=Buy, 2=Sell
    Reward: Risk-adjusted PnL (normalized)
    """

    def __init__(self, data: np.ndarray, initial_balance: float = 10000.0,
                 window_size: int = 60, commission: float = 0.0002):
        if GYM_AVAILABLE:
            super().__init__()
        # Pre-cast to float32 for performance and consistency with Gym spaces
        self.data = data.astype(np.float32)
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        # Pre-calculate rolling mean and std for O(1) observation generation
        df = pd.DataFrame(self.data)
        self.rolling_means = df.rolling(window=window_size).mean().values.astype(np.float32)
        # Use ddof=0 to match numpy.std() default
        self.rolling_stds = df.rolling(window=window_size).std(ddof=0).values.astype(np.float32)

        n_features = data.shape[1]
        self.n_features = n_features

        # Observation: window of market data + portfolio state [balance, position]
        if GYM_AVAILABLE:
            self.observation_space = gym.spaces.Box(
                low=-np.inf, high=np.inf,
                shape=(window_size * n_features + 2,),
                dtype=np.float32
            )
            # Actions: 0=Hold, 1=Buy, 2=Sell
            self.action_space = gym.spaces.Discrete(3)

        # Pre-allocate observation buffer to reduce GC pressure
        self.obs_buffer = np.zeros((window_size * n_features + 2,), dtype=np.float32)

        self.reset()

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        if GYM_AVAILABLE:
            super().reset(seed=seed)
        self.balance = self.initial_balance
        self.position = 0.0  # Current position in lots
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0
        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        current_price = self.data[self.current_step, 3]  # Close price
        reward = 0.0

        # Execute action
        if action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            self.entry_price = current_price * (1 + self.commission)
        elif action == 2 and self.position == 1:  # Sell / Close Long
            pnl = (current_price * (1 - self.commission)) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
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
            "total_pnl": self.total_pnl
        }
        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        # Vectorized and pre-calculated observation generation

        # rolling_means[i] is mean of data[i-W+1 : i+1]
        # We want mean of data[current_step - window_size : current_step]
        # This corresponds to index current_step - 1
        idx = self.current_step - 1
        mean = self.rolling_means[idx]
        std = self.rolling_stds[idx]

        window = self.data[self.current_step - self.window_size:self.current_step]
        obs = (window - mean) / (std + 1e-8)

        # Use buffer and ravel() to avoid unnecessary copies
        self.obs_buffer[:self.window_size * self.n_features] = obs.ravel()
        self.obs_buffer[-2] = self.balance / self.initial_balance
        self.obs_buffer[-1] = self.position

        return self.obs_buffer.copy()

    def render(self):
        print(f"Step: {self.current_step} | Balance: ${self.balance:.2f} | Position: {self.position}")

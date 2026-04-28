"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/environment/gym_env.py
Custom Gymnasium trading environment for RL training.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import gymnasium as gym
import numpy as np


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
        self.data = data
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        n_features = data.shape[1]

        # Observation: window of market data + portfolio state [balance, position]
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(window_size * n_features + 2,),
            dtype=np.float32
        )

        # Actions: 0=Hold, 1=Buy, 2=Sell
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
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
        window = self.data[self.current_step - self.window_size:self.current_step]
        # Normalize window
        obs = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
        portfolio_state = np.array([self.balance / self.initial_balance, self.position], dtype=np.float32)
        return np.concatenate([obs.flatten(), portfolio_state]).astype(np.float32)

    def render(self):
        logger.info(
            "Step: %d | Balance: $%.2f | Position: %.2f",
            self.current_step,
            self.balance,
            self.position,
        )

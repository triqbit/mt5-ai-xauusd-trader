"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Custom Gymnasium trading environment for XAUUSD trading.
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
        commission: float = 0.0002
    ):
        """
        Initialize the trading environment.

        Args:
            data: Historical market data with indicators (num_bars, num_features).
            initial_balance: Starting account balance.
            window_size: Number of lookback periods for observation.
            commission: Per-trade commission as a fraction.
        """
        super().__init__()
        self.data = data.astype(np.float32)
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        n_features = data.shape[1]

        # Observation: window of market data + portfolio state [balance_norm, position]
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + 2,),
            dtype=np.float32
        )

        # Actions: 0=Hold, 1=Buy, 2=Sell
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """Reset the environment to the initial state."""
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.position = 0.0  # 0: None, 1: Long, -1: Short (Simplified to 1/0 for now)
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0

        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one timestep within the environment.

        Args:
            action: 0=Hold, 1=Buy, 2=Sell
        """
        if self.current_step >= len(self.data) - 1:
            return self._get_observation(), 0.0, True, False, {}

        current_price = self.data[self.current_step, 3]  # Close price assumed at index 3
        reward = 0.0

        # Execute action
        # 1: Buy (Open Long if not in position)
        if action == 1 and self.position == 0:
            self.position = 1.0
            self.entry_price = current_price * (1 + self.commission)

        # 2: Sell (Close Long if in position)
        elif action == 2 and self.position == 1:
            pnl = (current_price * (1 - self.commission)) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            reward = (pnl / self.initial_balance) * 100.0  # Scaled reward
            self.position = 0.0
            self.entry_price = 0.0

        # Unrealized PnL reward for holding position
        if self.position == 1:
            unrealized = current_price - self.entry_price
            reward += (unrealized / self.initial_balance)

        self.current_step += 1

        terminated = self.balance <= (self.initial_balance * 0.5) or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_pnl": self.total_pnl,
            "step": self.current_step
        }

        return self._get_observation(), float(reward), terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """Construct the observation vector."""
        start = self.current_step - self.window_size
        window = self.data[start:self.current_step]

        # Simple normalization
        mu = window.mean(axis=0)
        sigma = window.std(axis=0) + 1e-8
        obs = (window - mu) / sigma

        portfolio_state = np.array([
            self.balance / self.initial_balance,
            self.position
        ], dtype=np.float32)

        return np.concatenate([obs.flatten(), portfolio_state]).astype(np.float32)

    def render(self):
        """Render the environment state (console)."""
        logger.info(
            "Step: %d | Balance: %.2f | Position: %.1f",
            self.current_step, self.balance, self.position
        )

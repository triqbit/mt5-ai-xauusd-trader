"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Custom Gymnasium trading environment for XAUUSD.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np

logger = logging.getLogger(__name__)


class TradingEnv(gym.Env):
    """
    Gymnasium-compatible environment for XAUUSD trading.
    Standard interface for RL agents (PPO, DreamerV3, etc.).
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        data: np.ndarray,
        initial_balance: float = 10000.0,
        window_size: int = 60,
        commission: float = 0.0002,
        render_mode: Optional[str] = None
    ) -> None:
        super().__init__()
        self.data = data
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission
        self.render_mode = render_mode

        n_features = data.shape[1]

        # Observation: window of market data + [balance_ratio, current_position]
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
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the environment to an initial state."""
        super().reset(seed=seed)

        self.balance = self.initial_balance
        self.position = 0.0  # 0.0=None, 1.0=Long, -1.0=Short
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0

        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Executes one timestep within the environment."""
        if self.current_step >= len(self.data) - 1:
            return self._get_observation(), 0.0, True, False, {}

        current_price = self.data[self.current_step, 3]  # Assuming index 3 is Close
        reward = 0.0

        # Simple execution logic for the skeleton
        if action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            self.entry_price = current_price * (1 + self.commission)
        elif action == 2 and self.position == 1:  # Sell (Close Long)
            pnl = (current_price * (1 - self.commission)) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            reward = pnl / self.initial_balance
            self.position = 0.0
            self.entry_price = 0.0

        self.current_step += 1

        terminated = self.balance <= self.initial_balance * 0.5 or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_pnl": self.total_pnl,
            "step": self.current_step
        }

        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """Constructs the observation vector."""
        window = self.data[self.current_step - self.window_size : self.current_step]
        # Basic normalization
        obs = (window - np.mean(window, axis=0)) / (np.std(window, axis=0) + 1e-8)

        portfolio_state = np.array(
            [self.balance / self.initial_balance, self.position],
            dtype=np.float32
        )

        return np.concatenate([obs.flatten(), portfolio_state]).astype(np.float32)

    def render(self) -> None:
        """Renders the environment."""
        if self.render_mode == "human":
            print(f"Step: {self.current_step} | Balance: {self.balance:.2f} | Position: {self.position}")

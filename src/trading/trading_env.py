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


class XAUUSDTradingEnv(gym.Env):
    """
    Custom Gymnasium environment for XAUUSD (Gold) trading.
    Adheres to institutional standards for state representation and reward shaping.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        data: np.ndarray,
        initial_balance: float = 10000.0,
        window_size: int = 60,
        commission: float = 0.0002,
        leverage: float = 10.0,
    ) -> None:
        super().__init__()
        self.data = data
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission
        self.leverage = leverage

        n_features = data.shape[1]

        # Observation space: Window of market data + [balance, position, unrealized_pnl]
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + 3,),
            dtype=np.float32,
        )

        # Actions: 0 = Hold, 1 = Buy, 2 = Sell
        self.action_space = gym.spaces.Discrete(3)

        self.reset()

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset the environment to initial state."""
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.position = 0.0  # 1.0 for Long, -1.0 for Short, 0.0 for None
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0

        return self._get_observation(), {}

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Execute one step in the environment."""
        if self.current_step >= len(self.data) - 1:
            return self._get_observation(), 0.0, True, False, {}

        # Action mapping: 0=Hold, 1=Buy, 2=Sell
        # Close price is at index 3 (standard OHLCV)
        current_price = self.data[self.current_step, 3]
        reward = 0.0

        # Simple execution logic for the skeleton
        if action == 1 and self.position <= 0:  # Switch to Long
            if self.position == -1:  # Close Short
                reward += self._close_position(current_price)
            self._open_position(current_price, 1.0)
        elif action == 2 and self.position >= 0:  # Switch to Short
            if self.position == 1:  # Close Long
                reward += self._close_position(current_price)
            self._open_position(current_price, -1.0)
        elif action == 0 and self.position != 0: # Hold but maybe close if exit signal? (Optional)
             pass

        self.current_step += 1

        # Calculate step reward (incremental PnL + penalty for holding)
        step_pnl = 0.0
        if self.position != 0:
            price_diff = current_price - self.data[self.current_step - 1, 3]
            step_pnl = price_diff * self.position * self.leverage
            reward += step_pnl / self.initial_balance

        self.total_pnl += step_pnl
        self.balance += step_pnl

        terminated = self.balance <= self.initial_balance * 0.5 or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_pnl": self.total_pnl,
            "step": self.current_step,
        }

        return self._get_observation(), reward, terminated, truncated, info

    def _open_position(self, price: float, side: float) -> None:
        self.position = side
        self.entry_price = price * (1 + (side * self.commission))

    def _close_position(self, price: float) -> float:
        pnl = (price - self.entry_price) * self.position * self.leverage
        # Commission on closing
        pnl -= price * self.commission * self.leverage
        self.position = 0.0
        self.entry_price = 0.0
        return pnl / self.initial_balance

    def _get_observation(self) -> np.ndarray:
        """Construct the observation vector."""
        window = self.data[self.current_step - self.window_size : self.current_step]
        # Flatten and normalize (simplified)
        obs = window.flatten().astype(np.float32)
        # Append portfolio state
        state = np.array(
            [
                self.balance / self.initial_balance,
                self.position,
                (self.total_pnl / self.initial_balance) if self.initial_balance > 0 else 0,
            ],
            dtype=np.float32,
        )
        return np.concatenate([obs, state])

    def render(self) -> None:
        """Optional: Render the environment state."""
        print(
            f"Step: {self.current_step} | Balance: {self.balance:.2f} | "
            f"Pos: {self.position} | PnL: {self.total_pnl:.2f}"
        )

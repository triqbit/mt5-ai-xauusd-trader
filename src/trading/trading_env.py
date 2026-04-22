"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Gymnasium-compatible environment skeleton for XAUUSD trading.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    import gymnasium as gym
except ImportError:
    # Lazy import fallback for CI environments without gymnasium
    gym = None

logger = logging.getLogger(__name__)


class XAUUSDTradingEnv(gym.Env if gym else object):
    """
    Custom Gymnasium environment for XAUUSD trading.
    State: OHLCV + technical indicators + portfolio state.
    Actions: 0=Hold, 1=Buy, 2=Sell.
    """

    def __init__(
        self,
        data: np.ndarray,
        initial_balance: float = 10000.0,
        window_size: int = 60,
        commission: float = 0.0002,
    ) -> None:
        if gym is None:
            logger.warning("Gymnasium not installed. XAUUSDTradingEnv acting as stub.")
            return

        super().__init__()
        self.data = data
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        # Features + [balance_ratio, current_position]
        n_features = data.shape[1]
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + 2,),
            dtype=np.float32,
        )

        # Actions: 0=Hold, 1=Buy, 2=Sell
        self.action_space = gym.spaces.Discrete(3)
        self.reset()

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset the environment to its initial state."""
        if gym is not None:
            super().reset(seed=seed)

        self.balance = self.initial_balance
        self.position = 0.0  # 0: None, 1: Long, 2: Short
        self.current_step = self.window_size
        self.total_pnl = 0.0

        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one environment step.
        """
        # Basic step logic skeleton
        reward = 0.0
        self.current_step += 1

        terminated = self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "position": self.position,
            "pnl": self.total_pnl,
            "step": self.current_step,
        }

        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        """
        Generate observation for the current step.
        """
        if self.data is None or self.current_step < self.window_size:
            # Return zero observation if data is not available
            # Better to use the space shape if available
            if hasattr(self, "observation_space"):
                return np.zeros(self.observation_space.shape, dtype=np.float32)
            return np.zeros(2, dtype=np.float32)

        window = self.data[self.current_step - self.window_size : self.current_step]
        # Basic normalization for skeleton
        obs_window = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
        portfolio_state = np.array(
            [self.balance / self.initial_balance, self.position], dtype=np.float32
        )
        return np.concatenate([obs_window.flatten(), portfolio_state]).astype(np.float32)

    def render(self) -> None:
        """Render the environment state."""
        logger.info(
            "Step: %d | Balance: %.2f | Position: %.1f",
            self.current_step,
            self.balance,
            self.position,
        )

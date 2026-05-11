"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/trading/trading_env.py
Custom Gymnasium-compatible environment for XAUUSD trading.
"""

from __future__ import annotations

import logging
from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces


class TradingEnv(gym.Env):
    """
    Custom environment for trading XAUUSD.

    Follows Gymnasium API. Optimized for high-frequency RL training.
    This environment simulates trading Gold (XAUUSD) using historical OHLCV data.

    Attributes:
        df: DataFrame containing historical market data.
        window_size: Number of past time steps to include in the observation.
        initial_balance: Starting account balance in USD.
        action_space: Discrete(3) - 0: HOLD/NEUTRAL, 1: BUY/LONG, 2: SELL/SHORT.
        observation_space: Box(window_size, num_features) - Historical price/indicator window.

    Examples:
        >>> env = TradingEnv(df=price_df, window_size=20)
        >>> obs, info = env.reset()
        >>> action = env.action_space.sample()
        >>> obs, reward, terminated, truncated, info = env.step(action)
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame | None = None,
        window_size: int = 20,
        initial_balance: float = 10000.0,
        column_mapping: dict[str, int] | None = None,
        spread: float = 0.20,
        slippage: float = 0.05,
    ) -> None:
        """
        Initializes the trading environment.

        Args:
            df: Optional DataFrame containing historical market data.
                Required columns: 'Open', 'High', 'Low', 'Close', 'Volume' (at minimum).
            window_size: Number of past time steps to include in the observation.
            initial_balance: Starting account balance.
            column_mapping: Optional mapping of column names to indices.
            spread: Trading spread for XAUUSD (default: 0.20 USD).
            slippage: Expected slippage per trade (default: 0.05 USD).
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.df = df
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.spread = spread
        self.slippage = slippage

        # Default column mapping if none provided
        self.column_mapping = column_mapping or {
            "open": 0,
            "high": 1,
            "low": 2,
            "close": 3,
            "volume": 4,
        }

        # Actions: 0 = HOLD, 1 = BUY, 2 = SELL
        self.action_space = spaces.Discrete(3)

        # Observation space: Window of features
        # Assuming features are normalized (z-score or min-max)
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
        self.position = 0  # 0: None, 1: Long, -1: Short
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
            A tuple containing the initial observation and an info dictionary.
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

        The default reward function is based on log returns of the equity.
        For production, consider reward shaping:
        - Penalizing drawdowns
        - Scaling by volatility (Sharpe-like)
        - Adding small penalties for excessive switching (transaction costs)

        Args:
            action: The action to take (0=HOLD, 1=BUY, 2=SELL).

        Returns:
            A tuple containing (observation, reward, terminated, truncated, info).
        """
        self.current_step += 1

        reward = 0.0
        if self._data is not None and self.current_step < len(self._data):
            close_idx = self.column_mapping.get("close", 3)
            current_price = self._data[self.current_step, close_idx]
            prev_price = self._data[self.current_step - 1, close_idx]

            # Update equity based on open position (unrealized P&L)
            if self.position == 1:  # Long
                unrealized_pnl = current_price - prev_price
                self.equity += unrealized_pnl
                # Reward based on price change (log returns often preferred for training)
                reward = float(np.log(current_price / prev_price))
            elif self.position == -1:  # Short
                unrealized_pnl = prev_price - current_price
                self.equity += unrealized_pnl
                reward = float(np.log(prev_price / current_price))

            # Handle actions (0=HOLD, 1=BUY, 2=SELL)
            if action == 1:  # LONG
                if self.position == -1:  # Close short
                    realized_pnl = (
                        self.entry_price - current_price - (self.spread + self.slippage)
                    )
                    self.balance += realized_pnl
                    self.position = 0

                if self.position == 0:  # Open long
                    self.position = 1
                    self.entry_price = current_price + (self.spread + self.slippage)
                    self.equity -= self.spread + self.slippage  # Immediate cost

            elif action == 2:  # SHORT
                if self.position == 1:  # Close long
                    realized_pnl = (
                        current_price - self.entry_price - (self.spread + self.slippage)
                    )
                    self.balance += realized_pnl
                    self.position = 0

                if self.position == 0:  # Open short
                    self.position = -1
                    self.entry_price = current_price - (self.spread + self.slippage)
                    self.equity -= self.spread + self.slippage  # Immediate cost

            elif action == 0:  # HOLD / CLOSE
                # Implementation choice: 0 closes all positions
                if self.position != 0:
                    if self.position == 1:
                        realized_pnl = (
                            current_price - self.entry_price - (self.spread + self.slippage)
                        )
                    else:
                        realized_pnl = (
                            self.entry_price - current_price - (self.spread + self.slippage)
                        )
                    self.balance += realized_pnl
                    self.position = 0

            # Apply transaction cost penalty to reward if an action was taken
            # to prevent excessive switching/churn.
            if action != 0:
                reward -= (self.spread + self.slippage) * 0.0001  # Scaled penalty

        terminated = False
        if self._data is not None and self.current_step >= len(self._data) - 1:
            terminated = True
            # Close any open position at the end to realize final P&L
            if self.position != 0:
                self.balance = self.equity
                self.position = 0

        truncated = False
        obs = self._get_observation()

        # Metadata for auditing and reward shaping analysis
        info = {
            "step": self.current_step,
            "action": action,
            "reward": reward,
            "balance": float(self.balance),
            "equity": float(self.equity),
            "position": self.position,
            "entry_price": float(self.entry_price),
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

        # Vectorized slicing for speed
        return self._data[self.current_step - self.window_size : self.current_step]

    def render(self) -> None:
        """
        Renders the current state of the environment for debugging.
        """
        self.logger.info(
            f"Step: {self.current_step} | Balance: {self.balance:.2f} | "
            f"Equity: {self.equity:.2f} | Position: {self.position}"
        )

    def close(self) -> None:
        """
        Performs any necessary cleanup when the environment is closed.
        """
        self.logger.debug("Closing TradingEnv.")


__all__ = ["TradingEnv"]

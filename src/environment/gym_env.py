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
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class TradingEnv(gym.Env):
    """
    Custom Gymnasium environment for XAUUSD trading.
    State: OHLCV + technical indicators (SMA, RSI) + portfolio state
    Actions: 0=Hold, 1=Buy, 2=Sell
    Reward: Risk-adjusted PnL with drawdown penalty
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, data: np.ndarray, initial_balance: float = 10000.0,
                 window_size: int = 60, commission: float = 0.0002):
        super().__init__()

        # Convert raw numpy data to DataFrame for technical indicators
        df = pd.DataFrame(data, columns=["open", "high", "low", "close", "tick_volume"])

        # Add Technical Indicators
        df["sma_20"] = ta.sma(df["close"], length=20)
        df["sma_50"] = ta.sma(df["close"], length=50)
        df["rsi_14"] = ta.rsi(df["close"], length=14)

        # Drop NaN values from indicators
        self.df = df.dropna().reset_index(drop=True)
        self.data = self.df.values

        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission

        n_features = self.data.shape[1]

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
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance
        self.position = 0.0  # Current position in lots
        self.entry_price = 0.0
        self.current_step = self.window_size
        self.total_pnl = 0.0
        return self._get_observation(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        current_price = self.data[self.current_step, 3]  # Close price is index 3
        reward = 0.0

        # 1. Execute action
        if action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            self.entry_price = current_price * (1 + self.commission)
        elif action == 2 and self.position == 1:  # Sell / Close Long
            pnl = (current_price * (1 - self.commission)) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            reward = pnl / self.initial_balance * 100  # Base reward
            self.position = 0.0
            self.entry_price = 0.0

        # 2. Update Equity & Drawdown
        if self.position == 1:
            self.equity = self.balance + (current_price - self.entry_price)
        else:
            self.equity = self.balance

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        drawdown = (self.peak_equity - self.equity) / self.peak_equity

        # 3. Reward Shaping: Penalize Drawdown
        if drawdown > 0.05:  # 5% drawdown penalty
            reward -= (drawdown * 10)

        self.current_step += 1

        terminated = self.balance <= self.initial_balance * 0.5 or self.current_step >= len(self.data) - 1
        truncated = False

        info = {
            "balance": self.balance,
            "equity": self.equity,
            "position": self.position,
            "drawdown": drawdown,
            "total_pnl": self.total_pnl
        }
        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        window = self.data[self.current_step - self.window_size:self.current_step]
        # Normalize window
        obs = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
        portfolio_state = np.array([self.equity / self.initial_balance, self.position], dtype=np.float32)
        return np.concatenate([obs.flatten(), portfolio_state]).astype(np.float32)

    def render(self):
        print(f"Step: {self.current_step} | Equity: ${self.equity:.2f} | Position: {self.position}")

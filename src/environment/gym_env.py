"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/environment/gym_env.py
Custom Gymnasium trading environment for RL training.
Integrated with FeatureEngineer for high-dimensional state representation.
"""

import gymnasium as gym
import numpy as np
import pandas as pd
import logging
from typing import Optional, Tuple, Dict, Any

from src.models.feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)

class TradingEnv(gym.Env):
    """
    Custom Gymnasium environment for XAUUSD trading.
    State: OHLCV + technical indicators (via FeatureEngineer)
    Actions: 0=Hold, 1=Buy, 2=Sell
    Reward: Risk-adjusted PnL (normalized)
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, data: pd.DataFrame, initial_balance: float = 10000.0,
                 window_size: int = 60, commission: float = 0.0002,
                 feature_engineer: Optional[FeatureEngineer] = None):
        super().__init__()

        self.fe = feature_engineer or FeatureEngineer()

        # Process data through feature engineer
        processed_data = self.fe.generate_features(data)
        # Drop rows with NaNs caused by indicators
        before_drop = len(processed_data)
        processed_data = processed_data.dropna()
        after_drop = len(processed_data)

        if after_drop == 0:
            logger.error(f"All data rows were dropped after feature generation. Before: {before_drop}, After: {after_drop}")
            # Log some of the NaNs to see which columns are causing it
            nan_counts = processed_data.isna().sum() if before_drop > 0 else "N/A"
            logger.error(f"NaN counts per column: {nan_counts}")

        # Separate OHLC for price reference and features for observation
        self.raw_data = processed_data[['open', 'high', 'low', 'close', 'volume']].values
        self.features = processed_data[self.fe.feature_columns].values

        self.initial_balance = initial_balance
        self.window_size = window_size
        self.commission = commission
        
        n_features = self.features.shape[1]
        
        # Observation: window of features + portfolio state [balance, position]
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
        # raw_data index matches features index because they come from same processed_data
        current_price = self.raw_data[self.current_step, 3]  # Close price
        reward = 0.0

        # Execute action
        if action == 1 and self.position == 0:  # Buy
            self.position = 1.0
            self.entry_price = current_price * (1 + self.commission)
        elif action == 2 and self.position == 1:  # Sell / Close Long
            pnl = (current_price * (1 - self.commission)) - self.entry_price
            self.balance += pnl
            self.total_pnl += pnl
            # reward = pnl / self.initial_balance * 100 # We'll use step-wise reward instead
            self.position = 0.0
            self.entry_price = 0.0
        
        # Step-wise reward: Change in portfolio value
        new_price = self.raw_data[self.current_step + 1, 3] if self.current_step < len(self.features) - 1 else current_price

        if self.position == 1:
            # Reward is the price change
            price_change = (new_price - current_price) / current_price
            reward = price_change * 100 # Normalized percentage reward

        self.current_step += 1
        
        terminated = self.balance <= self.initial_balance * 0.5 or self.current_step >= len(self.features) - 1
        truncated = False
        
        info = {
            "balance": self.balance, 
            "position": self.position,
            "total_pnl": self.total_pnl,
            "step": self.current_step
        }
        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self) -> np.ndarray:
        # Get window from features
        window = self.features[self.current_step - self.window_size:self.current_step]
        # Normalize window (Z-score)
        obs = (window - window.mean(axis=0)) / (window.std(axis=0) + 1e-8)
        # Portfolio state
        portfolio_state = np.array([self.balance / self.initial_balance, self.position], dtype=np.float32)
        return np.concatenate([obs.flatten(), portfolio_state]).astype(np.float32)

    def render(self):
        print(f"Step: {self.current_step} | Balance: ${self.balance:.2f} | Position: {self.position}")

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from src.models.base import BaseModel, Signal


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Wraps Stable-Baselines3 PPO for use in the trading ensemble.
    """

    def __init__(
        self,
        env: Optional[object] = None,
        model_path: Optional[Path] = None,
        device: str = "auto",
    ):
        """
        Initialise PPO Agent.

        Args:
            env: Gymnasium environment.
            model_path: Path to a saved PPO model.
            device: Computing device ('cpu', 'cuda', 'auto').
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            logging.warning("Stable-Baselines3 not installed. PPOAgent restricted.")
            self.model = None
            return

        self.logger = logging.getLogger(__name__)
        self.device = device

        if model_path and Path(model_path).exists():
            self.logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(model_path, device=device)
        elif env:
            self.env = DummyVecEnv([lambda: env])
            self.logger.info("Creating new PPO model...")
            self.model = PPO(
                policy="MlpPolicy",
                env=self.env,
                verbose=1,
                device=device,
            )
        else:
            self.model = None
            self.logger.warning("No environment or model path provided for PPOAgent.")

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading action from the current features.

        Args:
            features: Input features for the model.

        Returns:
            Signal: direction (1=Buy, -1=Sell, 0=Hold) and confidence.
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0)

        action, _states = self.model.predict(features, deterministic=True)

        # Action mapping: 0=Hold, 1=Buy, 2=Sell
        # Standardised direction: 1=Buy, -1=Sell, 0=Hold
        direction_map = {0: 0, 1: 1, 2: -1}

        # Handle potential array input/output from vectorized environments
        if isinstance(action, np.ndarray):
            action_val = int(action[0])
        else:
            action_val = int(action)

        direction = direction_map.get(action_val, 0)

        # PPO predict doesn't return confidence directly without accessing policy.
        # Stubbing confidence as 1.0 for now for deterministic actions.
        return Signal(direction=direction, confidence=1.0)

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None):
        """Train the PPO agent."""
        if self.model:
            self.model.learn(total_timesteps=total_timesteps)
            if save_path:
                self.model.save(save_path)

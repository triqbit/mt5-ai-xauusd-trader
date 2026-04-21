"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from src.models.base_model import BaseModel, Signal


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Wraps Stable-Baselines3 PPO for production trading.
    """

    def __init__(
        self, env=None, model_path: Optional[Union[str, Path]] = None, device: str = "auto"
    ):
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.env = DummyVecEnv([lambda: env]) if env else None
        self.model: Optional[PPO] = None

        if model_path and Path(model_path).exists():
            self.logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(str(model_path), env=self.env, device=device)
        elif self.env:
            self.logger.info("Creating new PPO model...")
            self.model = PPO(
                policy="MlpPolicy",
                env=self.env,
                verbose=1,
                device=device,
            )

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from the current observation.

        Args:
            features: Observation vector from the environment.

        Returns:
            Signal object (direction, confidence).
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0)

        action, _states = self.model.predict(features, deterministic=True)

        # Action mapping: 0=Hold, 1=Buy, 2=Sell
        # Signal direction mapping: 1=Buy, -1=Sell, 0=Hold
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(int(action), 0)

        return Signal(
            direction=direction, confidence=1.0
        )  # PPO discrete action has 100% confidence in its choice

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None):
        """Train the PPO agent."""
        if not self.model:
            raise ValueError("Model or Env not initialized for training.")

        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(str(save_path))
            self.logger.info(f"Model saved to {save_path}")

    def predict(self, observation):
        """Generate a trading action from the current observation."""
        action, _states = self.model.predict(observation, deterministic=True)
        return action

    def evaluate(self, n_eval_episodes: int = 10) -> dict:
        """Evaluate agent performance over n episodes."""
        from stable_baselines3.common.evaluation import evaluate_policy

        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": mean_reward, "std_reward": std_reward}

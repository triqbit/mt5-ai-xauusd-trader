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
    Inherits from BaseModel and wraps Stable-Baselines3 PPO.
    """

    def __init__(
        self,
        env=None,
        model_path: Optional[Path] = None,
        device: str = "auto"
    ):
        """
        Initialize PPO agent.

        Args:
            env: Gymnasium-compatible environment.
            model_path: Path to a saved PPO model.
            device: Computing device (cpu, cuda, auto).
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            logging.error("Stable-Baselines3 not installed. RL features disabled.")
            raise

        self.logger = logging.getLogger(__name__)
        self.device = device

        if env:
            self.env = DummyVecEnv([lambda: env])
        else:
            self.env = None

        if model_path and Path(model_path).exists():
            self.logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(model_path, env=self.env, device=device)
        else:
            self.logger.info("Creating new PPO model...")
            self.model = PPO(
                policy="MlpPolicy",
                env=self.env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                vf_coef=0.5,
                max_grad_norm=0.5,
                verbose=1,
                device=device,
            )

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Observation vector from the environment.

        Returns:
            Signal: direction (+1 buy, -1 sell, 0 hold) and confidence.
        """
        # Ensure correct shape for SB3 (requires batch dim)
        if features.ndim == 1:
            features = features.reshape(1, -1)

        action, _states = self.model.predict(features, deterministic=True)

        # SB3 predict returns an array if input is batched
        act = int(action[0]) if isinstance(action, np.ndarray) else int(action)

        # Mapping: 0=Hold, 1=Buy, 2=Sell -> Signal direction (+1, -1, 0)
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(act, 0)

        # PPO deterministic predict doesn't easily expose probabilities without internal access
        # For the stub, we use 1.0 confidence for the chosen action
        return Signal(direction=direction, confidence=1.0)

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None):
        """Train the PPO agent."""
        if not self.env:
            raise ValueError("Environment must be provided for training.")

        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(save_path)
            self.logger.info(f"Model saved to {save_path}")

    def evaluate(self, n_eval_episodes: int = 10) -> dict:
        """Evaluate agent performance."""
        from stable_baselines3.common.evaluation import evaluate_policy

        if not self.env:
            raise ValueError("Environment must be provided for evaluation.")

        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": mean_reward, "std_reward": std_reward}

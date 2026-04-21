"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import torch

from .base_model import BaseModel, Signal


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood and implements BaseModel interface.
    """

    def __init__(
        self,
        env: Any = None,
        model_path: Optional[Path] = None,
        device: str = "auto",
    ) -> None:
        """
        Initialize the PPO agent.

        Args:
            env: Gymnasium environment instance.
            model_path: Path to a saved SB3 model.
            device: Device to run the model on ('cpu', 'cuda', 'auto').
        """
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv

        self.logger = logging.getLogger(__name__)
        self.device = device

        # Wrap environment for SB3
        if env is not None:
            self.env = DummyVecEnv([lambda: env])
        else:
            self.env = None

        if model_path and Path(model_path).exists():
            self.logger.info("Loading existing PPO model from %s", model_path)
            self.model = PPO.load(model_path, env=self.env, device=device)
        else:
            self.logger.info("Creating new PPO model...")
            # Default parameters for XAUUSD trading
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
        Generate a trading signal from the current observation.

        Args:
            features: Observation vector from the environment.

        Returns:
            Signal object with direction and confidence.
        """
        # Ensure features is the right shape (SB3 expects [batch, features])
        if features.ndim == 1:
            obs = features.reshape(1, -1)
        else:
            obs = features

        action, _ = self.model.predict(obs, deterministic=True)
        # SB3 predict returns an array of actions
        action_int = int(action[0]) if isinstance(action, (np.ndarray, list)) else int(action)

        # Attempt to get confidence from the policy's action distribution
        confidence = 1.0
        try:
            # We need to convert obs to tensor using the model's internal method
            obs_tensor, _ = self.model.policy.obs_to_tensor(obs)
            with torch.no_grad():
                distribution = self.model.policy.get_distribution(obs_tensor)
                # For Discrete action spaces, distribution is usually Categorical
                probs = distribution.distribution.probs.cpu().numpy()[0]
                confidence = float(probs[action_int])
        except Exception as e:
            self.logger.debug("Could not calculate PPO confidence: %s", e)

        # Mapping environment actions (0=Hold, 1=Buy, 2=Sell) to Signal direction
        # direction: 1 for Buy, -1 for Sell, 0 for Hold
        mapping = {0: 0, 1: 1, 2: -1}
        direction = mapping.get(action_int, 0)

        return Signal(
            direction=direction, confidence=confidence, metadata={"raw_action": action_int}
        )

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None) -> None:
        """Train the PPO agent."""
        self.logger.info("Starting PPO training for %d timesteps...", total_timesteps)
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(str(save_path))
            self.logger.info("Model saved to %s", save_path)

    def evaluate(self, n_eval_episodes: int = 10) -> Dict[str, float]:
        """Evaluate agent performance."""
        from stable_baselines3.common.evaluation import evaluate_policy

        if self.env is None:
            raise ValueError("Environment must be provided for evaluation.")

        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": float(mean_reward), "std_reward": float(std_reward)}

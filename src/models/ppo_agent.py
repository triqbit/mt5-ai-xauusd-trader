"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
Wraps the PPO algorithm for use with the custom Gymnasium trading environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from src.models.base import BaseModel, Signal


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    Inherits from BaseModel to provide a standard .predict() interface.
    """

    def __init__(
        self,
        env: Optional[Any] = None,
        model_path: Optional[Path] = None,
        device: str = "auto",
    ) -> None:
        """
        Initialize the PPO agent.

        Args:
            env: Gymnasium environment instance.
            model_path: Optional path to a saved SB3 model.
            device: Device to run the model on ('cpu', 'cuda', 'auto').
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            logging.error("stable-baselines3 not installed. PPOAgent will be unusable.")
            raise

        self.logger = logging.getLogger(__name__)
        self.device = device
        self._ppo_model: Optional[PPO] = None

        if env:
            self.env = DummyVecEnv([lambda: env])
        else:
            self.env = None

        if model_path and Path(model_path).exists():
            self.logger.info("Loading existing PPO model from %s", model_path)
            self._ppo_model = PPO.load(model_path, env=self.env, device=device)
        elif self.env:
            self.logger.info("Creating new PPO model...")
            self._ppo_model = PPO(
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

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None) -> None:
        """
        Train the PPO agent.

        Args:
            total_timesteps: Number of timesteps to train for.
            save_path: Optional path to save the trained model.
        """
        if not self._ppo_model:
            raise ValueError("Model not initialized with an environment.")

        self.logger.info("Starting PPO training for %d timesteps...", total_timesteps)
        self._ppo_model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self._ppo_model.save(str(save_path))
            self.logger.info("Model saved to %s", save_path)

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading action from the current observation.

        Args:
            features: Preprocessed observation from the environment.

        Returns:
            Signal object with direction, confidence, and metadata.
        """
        if not self._ppo_model:
            self.logger.warning("PPO model not loaded. Returning HOLD signal.")
            return Signal(direction=0, confidence=0.0)

        # SB3 predict returns (action, _states)
        action, _states = self._ppo_model.predict(features, deterministic=True)

        # Action map: 0=Hold, 1=Buy, 2=Sell (assuming env convention)
        # Convert to Signal direction: +1 Buy, -1 Sell, 0 Hold
        action_idx = int(action)
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_idx, 0)

        # PPO doesn't natively return confidence unless we inspect the policy distribution
        # For now, we return 1.0 if an action is chosen, or use a placeholder.
        return Signal(
            direction=direction,
            confidence=1.0 if direction != 0 else 0.0,
            metadata={"raw_action": action_idx},
        )

    def evaluate(self, n_eval_episodes: int = 10) -> Dict[str, float]:
        """
        Evaluate agent performance over n episodes.

        Args:
            n_eval_episodes: Number of episodes for evaluation.

        Returns:
            Dict containing mean and std reward.
        """
        if not self._ppo_model or not self.env:
            return {"mean_reward": 0.0, "std_reward": 0.0}

        from stable_baselines3.common.evaluation import evaluate_policy

        mean_reward, std_reward = evaluate_policy(
            self._ppo_model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": float(mean_reward), "std_reward": float(std_reward)}

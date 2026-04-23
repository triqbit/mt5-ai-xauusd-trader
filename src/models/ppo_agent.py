"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
Wraps the PPO algorithm for use with the custom Gymnasium trading environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np

from src.models.base import BaseModel, Signal

if TYPE_CHECKING:
    import gymnasium as gym


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """

    def __init__(
        self,
        env: Optional[gym.Env] = None,
        model_path: Optional[Path] = None,
        device: str = "auto",
    ) -> None:
        # Lazy imports for CI compatibility
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv

        self.logger = logging.getLogger(__name__)
        self.device = device
        self.model: Optional[PPO] = None

        if env is not None:
            self.vec_env = DummyVecEnv([lambda: env])
        else:
            self.vec_env = None

        if model_path and Path(model_path).exists():
            self.logger.info("Loading existing PPO model from %s", model_path)
            self.model = PPO.load(model_path, env=self.vec_env, device=device)
        elif self.vec_env is not None:
            self.logger.info("Creating new PPO model...")
            self.model = PPO(
                policy="MlpPolicy",
                env=self.vec_env,
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

    def train(
        self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None
    ) -> None:
        """Train the PPO agent."""
        if self.model is None:
            raise ValueError("Model not initialised. Provide an environment to __init__.")

        self.logger.info(
            "Starting PPO training for %d timesteps...", total_timesteps
        )
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(save_path)
            self.logger.info("Model saved to %s", save_path)

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading action from the current observation.
        Mapping: Action 0 -> Hold (0), 1 -> Buy (1), 2 -> Sell (-1)
        """
        if self.model is None:
            self.logger.warning("PPO model not loaded. Returning HOLD signal.")
            return Signal(direction=0, confidence=0.0)

        # Predict returns action (int) and states (for RNN policies)
        action, _states = self.model.predict(features, deterministic=True)

        # Map SB3 action to standardised Signal direction
        # SB3: 0=Hold, 1=Buy, 2=Sell
        # Signal: 0=Hold, 1=Buy, -1=Sell
        mapping = {0: 0, 1: 1, 2: -1}
        direction = mapping.get(int(action), 0)

        # PPO doesn't give a direct confidence score like Softmax output easily
        # without accessing the policy network. Using 1.0 as placeholder for now.
        return Signal(direction=direction, confidence=1.0)

    def evaluate(self, n_eval_episodes: int = 10) -> Dict[str, Any]:
        """Evaluate agent performance over n episodes."""
        from stable_baselines3.common.evaluation import evaluate_policy

        if self.model is None or self.vec_env is None:
            raise ValueError("Model and environment must be initialised for evaluation.")

        mean_reward, std_reward = evaluate_policy(
            self.model, self.vec_env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": mean_reward, "std_reward": std_reward}

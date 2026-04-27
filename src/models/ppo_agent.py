"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
Wraps the PPO algorithm for use with the custom Gymnasium trading environment.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from src.models.base import BaseModel, Signal
from src.trading.trading_env import TradingEnv


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood and implements BaseModel interface.
    """

    def __init__(
        self,
        env: Optional[TradingEnv] = None,
        model_path: Optional[Path] = None,
        device: str = "auto"
    ) -> None:
        """
        Initialise the PPO Agent.

        Args:
            env: Gymnasium environment. Required for training.
            model_path: Path to a pre-trained model.
            device: Computing device ('cpu', 'cuda', or 'auto').
        """
        self.logger = logging.getLogger(__name__)
        self.device = device

        # If env is provided, wrap it for SB3
        self.venv = DummyVecEnv([lambda: env]) if env else None

        if model_path and Path(model_path).exists():
            self.logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(model_path, env=self.venv, device=device)
        else:
            if self.venv is None:
                self.logger.warning("No environment or model_path provided. PPO model not fully initialised.")
                self.model = None
            else:
                self.logger.info("Creating new PPO model...")
                self.model = PPO(
                    policy="MlpPolicy",
                    env=self.venv,
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
            save_path: Where to save the model after training.
        """
        if self.model is None:
            raise ValueError("Model not initialised. Provide an environment in __init__.")

        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(save_path)
            self.logger.info(f"Model saved to {save_path}")

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from the current observation.

        Args:
            features: The observation vector from the environment.

        Returns:
            Signal: Direction (+1 Buy, -1 Sell, 0 Hold) and confidence.
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0)

        action, _states = self.model.predict(features, deterministic=True)

        # Action space 0=Hold, 1=Buy, 2=Sell. Convert to Signal direction.
        # Note: SB3 predict returns scalar action for Discrete spaces.
        action_idx = int(action)
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_idx, 0)

        # SB3 PPO doesn't provide easy confidence for Discrete actions without accessing policy distribution
        # For now, we return 1.0 if an action is chosen, or 0.0 if not.
        confidence = 1.0 if direction != 0 else 0.0

        return Signal(direction=direction, confidence=confidence)

    def evaluate(self, n_eval_episodes: int = 10) -> dict:
        """
        Evaluate agent performance over n episodes.

        Args:
            n_eval_episodes: Number of episodes to evaluate.

        Returns:
            dict: Mean and std of rewards.
        """
        if self.model is None or self.venv is None:
            raise ValueError("Model or Environment not initialised.")

        from stable_baselines3.common.evaluation import evaluate_policy
        mean_reward, std_reward = evaluate_policy(
            self.model, self.venv, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": mean_reward, "std_reward": std_reward}

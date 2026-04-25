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
from src.trading.trading_env import TradingEnv


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """

    def __init__(
        self,
        env: Optional[TradingEnv] = None,
        model_path: Optional[Path] = None,
        device: str = "auto",
    ) -> None:
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.error("stable-baselines3 not installed. PPOAgent will not function.")
            self.model = None
            return

        self.logger = logging.getLogger(__name__)
        self.device = device

        if env is None:
            # Create a placeholder env if none provided (useful for inference only loading)
            env = TradingEnv()

        self.env = DummyVecEnv([lambda: env])

        if model_path and Path(model_path).exists():
            self.logger.info("Loading existing PPO model from %s", model_path)
            self.model = PPO.load(str(model_path), env=self.env, device=device)
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

    def train(
        self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None
    ) -> None:
        """Train the PPO agent."""
        if self.model is None:
            return

        self.logger.info("Starting PPO training for %d timesteps...", total_timesteps)
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            self.model.save(str(save_path))
            self.logger.info("Model saved to %s", save_path)

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading action from the current observation.
        0=Hold, 1=Buy, 2=Sell (mapped to Signal direction)
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0)

        action, _states = self.model.predict(features, deterministic=True)
        action_val = int(action)

        # Mapping action to Signal direction
        # action: 0=Hold, 1=Buy, 2=Sell
        # Signal direction: +1 (Buy), -1 (Sell), 0 (Hold)
        mapping = {0: 0, 1: 1, 2: -1}
        direction = mapping.get(action_val, 0)

        # PPO doesn't give direct confidence without accessing policy dist,
        # using placeholder 1.0 for now.
        return Signal(direction=direction, confidence=1.0)

    def evaluate(self, n_eval_episodes: int = 10) -> Dict[str, Any]:
        """Evaluate agent performance over n episodes."""
        if self.model is None:
            return {}

        from stable_baselines3.common.evaluation import evaluate_policy

        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": float(mean_reward), "std_reward": float(std_reward)}

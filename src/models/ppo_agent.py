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

logger = logging.getLogger(__name__)


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """

    def __init__(
        self,
        env: Any = None,
        model_path: Optional[Path | str] = None,
        device: str = "auto",
    ) -> None:
        """
        Initialise the PPO agent.

        Args:
            env: Gymnasium environment instance.
            model_path: Path to a saved PPO model.
            device: Computing device (cpu, cuda, auto).
        """
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv

        self.device = device
        self.model: Optional[PPO] = None

        if model_path and Path(model_path).exists():
            logger.info("Loading existing PPO model from %s", model_path)
            self.model = PPO.load(str(model_path), device=device)
            if env:
                self.model.set_env(DummyVecEnv([lambda: env]))
        elif env:
            logger.info("Creating new PPO model...")
            vec_env = DummyVecEnv([lambda: env])
            self.model = PPO(
                policy="MlpPolicy",
                env=vec_env,
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
        else:
            logger.warning("PPOAgent initialised without environment or model_path.")

    def train(
        self, total_timesteps: int = 1_000_000, save_path: Optional[Path | str] = None
    ) -> None:
        """Train the PPO agent."""
        if self.model is None:
            raise ValueError("Model not initialised. Provide an environment or load a model.")

        logger.info("Starting PPO training for %d timesteps...", total_timesteps)
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            p = Path(save_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(str(p))
            logger.info("Model saved to %s", p)

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from the current observation.

        Args:
            features: Current environment observation.

        Returns:
            Signal: Direction (1, -1, 0) and confidence.
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0)

        action, _states = self.model.predict(features, deterministic=True)
        # action is Discrete(3): 0=Hold, 1=Buy, 2=Sell
        # Map to Signal directions: 1=Buy, -1=Sell, 0=Hold
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map[int(action)]

        # PPO's predict doesn't directly return probability for the action
        # In a real scenario, we might extract the policy distribution.
        # For this stub, we return a placeholder confidence.
        return Signal(direction=direction, confidence=0.8)

    def evaluate(self, env: Any, n_eval_episodes: int = 10) -> Dict[str, float]:
        """Evaluate agent performance over n episodes."""
        from stable_baselines3.common.evaluation import evaluate_policy
        from stable_baselines3.common.vec_env import DummyVecEnv

        if self.model is None:
            return {"mean_reward": 0.0, "std_reward": 0.0}

        vec_env = DummyVecEnv([lambda: env])
        mean_reward, std_reward = evaluate_policy(
            self.model, vec_env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": float(mean_reward), "std_reward": float(std_reward)}

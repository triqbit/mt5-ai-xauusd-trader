"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
Wraps the PPO algorithm for use with the custom Gymnasium trading environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from src.models import BaseModel, Signal

logger = logging.getLogger(__name__)

class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """
    def __init__(
        self,
        env: Optional[Any] = None,
        model_path: Optional[Path] = None,
        device: str = "auto"
    ) -> None:
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
        except ImportError:
            logger.error("stable-baselines3 not installed. PPOAgent will be limited.")
            self.model = None
            return

        self.device = device

        if env is not None:
            self.env = DummyVecEnv([lambda: env])
        else:
            self.env = None

        if model_path and Path(model_path).exists():
            logger.info(f"Loading existing PPO model from {model_path}")
            self.model = PPO.load(str(model_path), env=self.env, device=device)
        elif self.env is not None:
            logger.info("Creating new PPO model...")
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
        else:
            self.model = None
            logger.warning("PPOAgent initialized without environment or model path.")

    def train(self, total_timesteps: int = 1_000_000, save_path: Optional[Path] = None) -> None:
        """Train the PPO agent."""
        if self.model is None:
            raise RuntimeError("Model not initialized. Provide an environment or model path.")

        logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps)

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(str(save_path))
            logger.info(f"Model saved to {save_path}")

    def predict(self, features: Any) -> Signal:
        """
        Generate a trading signal from the current observation.

        Args:
            features: The observation from the Gymnasium environment.

        Returns:
            A Signal object (+1 Buy, -1 Sell, 0 Hold).
        """
        if self.model is None:
            return Signal(direction=0, confidence=0.0, metadata={"error": "Model not loaded"})

        # SB3 predict returns (action, next_state)
        action, _states = self.model.predict(features, deterministic=True)

        # Mapping Discrete(3) actions back to directions:
        # Assuming: 0=Hold, 1=Buy, 2=Sell (as defined in trading_env.py)
        action_val = int(action)
        direction_map = {0: 0, 1: 1, 2: -1}
        direction = direction_map.get(action_val, 0)

        # SB3 PPO doesn't natively return confidence/probabilities without extra steps
        # For the stub, we provide a default confidence if it's not a hold
        confidence = 1.0 if direction != 0 else 0.0

        return Signal(
            direction=direction,
            confidence=confidence,
            metadata={"raw_action": action_val}
        )

    def evaluate(self, n_eval_episodes: int = 10) -> Dict[str, float]:
        """Evaluate agent performance over n episodes."""
        if self.model is None or self.env is None:
            return {"mean_reward": 0.0, "std_reward": 0.0}

        from stable_baselines3.common.evaluation import evaluate_policy
        mean_reward, std_reward = evaluate_policy(
            self.model, self.env, n_eval_episodes=n_eval_episodes
        )
        return {"mean_reward": float(mean_reward), "std_reward": float(std_reward)}

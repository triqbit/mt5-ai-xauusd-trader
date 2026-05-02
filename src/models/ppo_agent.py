"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

from src.models.base_model import BaseModel, Signal
from src.core.constants import ModelAction


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood.
    """
    def __init__(
        self,
        env: Optional[Any] = None,
        model_path: Optional[Union[str, Path]] = None,
        device: str = "auto"
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.model = None

        # Lazy loading of SB3 to avoid dependency issues in non-training environments
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv

            if env is not None:
                self.env = DummyVecEnv([lambda: env])
            else:
                self.env = None

            if model_path and Path(model_path).exists():
                self.logger.info(f"Loading existing PPO model from {model_path}")
                self.model = PPO.load(model_path, env=self.env, device=device)
            elif self.env is not None:
                self.logger.info("Creating new PPO model...")
                self.model = PPO(
                    policy="MlpPolicy",
                    env=self.env,
                    verbose=1,
                    device=device,
                )
        except ImportError:
            self.logger.warning("Stable-Baselines3 not installed. PPOAgent will be limited.")

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from the current observation.
        """
        if self.model is None:
            return Signal(direction=SignalDirection.HOLD, confidence=0.0, metadata={"error": "Model not loaded"})

        # SB3 predict returns (action, states)
        action, _states = self.model.predict(features, deterministic=True)

        # In a real implementation, we might derive confidence from action probabilities
        # For now, we use a placeholder confidence
        model_action = ModelAction(int(action))

        return Signal(
            direction=model_action.to_direction(),
            confidence=0.85,  # Placeholder
            metadata={"raw_action": int(action)}
        )

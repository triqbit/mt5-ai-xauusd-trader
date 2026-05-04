"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

from src.core.constants import ModelAction, SignalDirection
from src.models.base_model import BaseModel, Signal


class PPOAgent(BaseModel):
    """
    PPO-based reinforcement learning agent.
    Uses Stable-Baselines3 PPO under the hood for policy-based trading decisions.

    Attributes:
        logger: Logger instance for monitoring agent activity.
        device: Torch device to use for inference (e.g., 'cpu', 'cuda', 'auto').
        model: Loaded PPO model instance or None.
        env: Vectorized environment used for model loading/training.
    """

    def __init__(
        self,
        env: Any | None = None,
        model_path: str | Path | None = None,
        device: str = "auto",
    ) -> None:
        """
        Initializes the PPO agent with lazy loading for stable-baselines3.

        Args:
            env: An instance of the Gymnasium-compatible TradingEnv.
            model_path: Optional path to a pre-trained PPO model file (.zip).
            device: Computing device to use ('cpu', 'cuda', 'auto').
        """
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.model = None
        self.env = None

        # Lazy loading of SB3 to avoid dependency issues in non-training environments
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv

            if env is not None:
                # Wrap in DummyVecEnv as SB3 models expect vectorized environments
                self.env = DummyVecEnv([lambda: env])

            if model_path and Path(model_path).exists():
                self.logger.info(f"Loading existing PPO model from {model_path}")
                self.model = PPO.load(model_path, env=self.env, device=device)
            elif self.env is not None:
                self.logger.info("Creating new PPO model with MlpPolicy...")
                self.model = PPO(
                    policy="MlpPolicy",
                    env=self.env,
                    verbose=1,
                    device=device,
                )
            else:
                self.logger.debug("PPOAgent initialized without model or environment.")

        except ImportError as e:
            self.logger.warning(
                f"Stable-Baselines3 not installed. PPOAgent will be limited: {e}"
            )

    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features using the PPO policy.

        Args:
            features: Input feature array (e.g., OHLCV window).

        Returns:
            A Signal object containing direction, confidence, and metadata.
        """
        if self.model is None:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Model not loaded"},
            )

        try:
            # SB3 predict returns (action, states)
            # deterministic=True is used for production/inference consistency
            action, _states = self.model.predict(features, deterministic=True)

            # Convert numpy action to native Python int for indexing/mapping
            action_val = int(action)

            # Map categorical action (0, 1, 2) to ModelAction enum
            try:
                model_action = ModelAction(action_val)
                direction = model_action.to_direction()
            except ValueError:
                self.logger.error(f"Model returned invalid action index: {action_val}")
                return Signal(
                    direction=SignalDirection.HOLD,
                    confidence=0.0,
                    metadata={"error": f"Invalid action index {action_val}"},
                )

            # In RL, confidence is often derived from the action probability (policy logit)
            # For this stub, we use a placeholder or 1.0 since it's a deterministic policy choice
            # A production implementation would query the policy distribution
            return Signal(
                direction=direction,
                confidence=1.0,
                metadata={"raw_action": action_val, "policy_type": "deterministic"},
            )

        except Exception as e:
            self.logger.exception(f"Error during PPO prediction: {e}")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def save(self, path: str | Path) -> None:
        """
        Saves the PPO model to the specified path.

        Args:
            path: Target file path for the .zip model.
        """
        if self.model is not None:
            self.model.save(path)
            self.logger.info(f"PPO model saved to {path}")
        else:
            self.logger.error("Attempted to save PPOAgent but no model is loaded.")

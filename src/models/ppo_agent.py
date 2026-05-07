"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

from __future__ import annotations

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
    Compatible with Gymnasium-style trading environments.

    Attributes:
        logger: Logger instance for monitoring agent activity.
        device: Torch device to use for inference (e.g., 'cpu', 'cuda', 'auto').
        model: Loaded PPO model instance or None.
        env: Vectorized environment used for model loading/training.
        ppo_kwargs: Hyperparameters passed to the PPO constructor.
    """

    def __init__(
        self,
        env: Any | None = None,
        model_path: str | Path | None = None,
        device: str = "auto",
        ppo_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Initializes the PPO agent with lazy loading for stable-baselines3.

        Args:
            env: An instance of the Gymnasium-compatible TradingEnv.
            model_path: Optional path to a pre-trained PPO model file (.zip).
            device: Computing device to use ('cpu', 'cuda', 'auto').
            ppo_kwargs: Optional dictionary of hyperparameters for the PPO constructor.
        """
        self.logger = logging.getLogger(__name__)
        self.device = device
        self.model = None
        self.env = None
        self.ppo_kwargs = ppo_kwargs or {}

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
                # Combine default parameters with user-provided kwargs
                default_kwargs = {
                    "policy": "MlpPolicy",
                    "env": self.env,
                    "verbose": 1,
                    "device": device,
                }
                combined_kwargs = {**default_kwargs, **self.ppo_kwargs}
                self.model = PPO(**combined_kwargs)
            else:
                self.logger.debug("PPOAgent initialized without model or environment.")

        except ImportError as e:
            self.logger.warning(f"Stable-Baselines3 not installed. PPOAgent will be limited: {e}")

    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features using the PPO policy.

        Args:
            features: Input feature array (e.g., OHLCV window).
            **kwargs: Ignored.

        Returns:
            A Signal object containing direction, confidence, and metadata.
        """
        # Production-grade robustness: Check for NaN or Inf in input features
        if not np.isfinite(features).all():
            self.logger.error("Input features contain NaN or Inf values.")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Invalid features: NaN or Inf detected"},
            )

        if self.model is None:
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": "Model not loaded"},
            )

        try:
            # Ensure features have a batch dimension for SB3 (usually (batch, window_size, n_features))
            obs = features
            if obs.ndim == 1:
                # Add batch and window dimensions if only features provided
                obs = np.expand_dims(np.expand_dims(obs, axis=0), axis=0)
            elif obs.ndim == 2:
                # Add batch dimension if window x features provided
                obs = np.expand_dims(obs, axis=0)

            # SB3 predict returns (action, states)
            # deterministic=True is used for production/inference consistency
            action, _states = self.model.predict(obs, deterministic=True)

            # Convert numpy action to native Python int for indexing/mapping
            # SB3 might return a batch of actions even for a single observation
            action_val = int(action[0]) if action.ndim > 0 else int(action)

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

            # Extract probabilities for confidence
            confidence = 1.0
            probabilities = []
            try:
                import torch

                # Convert observation to torch tensor for the policy
                obs_tensor = torch.as_tensor(obs).to(self.model.device)

                # Get the distribution from the policy
                with torch.no_grad():
                    # For Discrete action spaces, this returns a Categorical distribution
                    distribution = self.model.policy.get_distribution(obs_tensor)
                    # distribution.distribution.probs has shape (batch, n_actions)
                    probs_batch = distribution.distribution.probs.cpu().numpy()
                    probs = probs_batch[0]  # Get probabilities for the first (and only) observation
                    probabilities = probs.tolist()
                    confidence = float(probs[action_val])
            except Exception as prob_err:
                self.logger.debug(f"Could not extract probabilities from policy: {prob_err}")

            return Signal(
                direction=direction,
                confidence=confidence,
                metadata={
                    "raw_action": action_val,
                    "policy_type": "deterministic",
                    "probabilities": probabilities,
                },
            )

        except Exception as e:
            self.logger.exception(f"Error during PPO prediction: {e}")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def train(self, total_timesteps: int = 10000, callback: Any | None = None) -> None:
        """
        Trains the PPO agent on the provided environment.

        Args:
            total_timesteps: Total number of steps to train for.
            callback: Optional callback for monitoring training.
        """
        if self.model is None:
            self.logger.error("Cannot train: No model or environment loaded.")
            return

        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps, callback=callback)
        self.logger.info("PPO training complete.")

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


__all__ = ["PPOAgent"]

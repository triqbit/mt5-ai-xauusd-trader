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

try:
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
except ImportError:
    torch = None
    PPO = None
    DummyVecEnv = None

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

    Examples:
        >>> from src.trading.trading_env import TradingEnv
        >>> env = TradingEnv(df=sample_df)
        >>> agent = PPOAgent(env=env)
        >>> agent.train(total_timesteps=10000)
        >>> signal = agent.predict(np.random.randn(20, 140))
    """

    def __init__(
        self,
        env: Any | None = None,
        model_path: str | Path | None = None,
        device: str = "auto",
        ppo_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Initializes the PPO agent.

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

        if PPO is None:
            self.logger.warning("Stable-Baselines3 not installed. PPOAgent will be limited.")
            return

        if env is not None and DummyVecEnv is not None:
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

    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features using the PPO policy.

        Args:
            features: Input feature array (e.g., OHLCV window).
            **kwargs: Ignored.

        Returns:
            A Signal object containing direction, confidence, and metadata.

        Raises:
            ValueError: If features contain NaN/Inf or have invalid shape.
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
            # Explicit shape validation and reshaping for production robustness
            obs = features.astype(np.float32)
            expected_shape = None
            if self.model is not None and hasattr(self.model, "observation_space"):
                expected_shape = self.model.observation_space.shape

            if obs.ndim == 1:
                # If only a single feature vector is provided, reshape to (1, 1, features)
                # or (1, window_size, features) if possible.
                if expected_shape and len(expected_shape) == 2:
                    if obs.shape[0] == expected_shape[1]:
                        obs = obs.reshape(1, 1, -1)
                    else:
                        obs = obs.reshape(1, *expected_shape)
                else:
                    obs = obs.reshape(1, 1, -1)
            elif obs.ndim == 2:
                # (window, features) -> (1, window, features)
                obs = np.expand_dims(obs, axis=0)
            elif obs.ndim > 3:
                self.logger.error(f"Invalid observation shape: {obs.shape}. Expected up to 3 dims.")
                raise ValueError(f"Invalid observation shape: {obs.shape}")

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
            if torch is not None:
                try:
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
            if isinstance(e, ValueError):
                raise e
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

        Raises:
            RuntimeError: If the model is not initialized or environment is missing.
        """
        if self.model is None:
            error_msg = "Cannot train: Model not initialized."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        if self.model.get_env() is None:
            error_msg = "Cannot train: No environment set in the PPO model."
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.logger.info(f"Starting PPO training for {total_timesteps} timesteps...")
        self.model.learn(total_timesteps=total_timesteps, callback=callback)
        self.logger.info("PPO training complete.")

    def save(self, path: str | Path) -> None:
        """
        Saves the PPO model to the specified path.

        Args:
            path: Target file path for the .zip model.

        Raises:
            IOError: If saving the model fails.
        """
        if self.model is not None:
            save_path = Path(path)
            # Ensure target directory exists before saving
            save_path.parent.mkdir(parents=True, exist_ok=True)

            self.model.save(save_path)
            self.logger.info(f"PPO model saved to {save_path}")
        else:
            self.logger.error("Attempted to save PPOAgent but no model is loaded.")


__all__ = ["PPOAgent"]

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/ppo_agent.py
Proximal Policy Optimization (PPO) agent using Stable-Baselines3.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

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
        env: Optional[Any] = None,
        model_path: Optional[Union[str, Path]] = None,
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
            import torch

            # SB3 models expect (batch, ...) observations.
            # If features is (window_size, n_features), add batch dim.
            if features.ndim == 2:
                obs = features[np.newaxis, ...]
            else:
                obs = features

            # Use the policy to get action probabilities for confidence estimation
            self.model.policy.set_training_mode(False)
            with torch.no_grad():
                # Convert to tensor and move to device
                obs_tensor, _ = self.model.policy.obs_to_tensor(obs)
                distribution = self.model.policy.get_distribution(obs_tensor)

                # For Discrete action space, we extract probabilities
                if hasattr(distribution.distribution, "probs"):
                    probs = distribution.distribution.probs.cpu().numpy()[0]
                else:
                    # Fallback for other distributions (e.g. continuous)
                    # For XAUUSD TradingEnv it is Discrete(3)
                    action, _ = self.model.predict(obs, deterministic=True)
                    return Signal(
                        direction=ModelAction(int(action[0])).to_direction(),
                        confidence=1.0,
                        metadata={"policy_type": "fallback"},
                    )

            action_val = int(np.argmax(probs))
            confidence = float(probs[action_val])

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

            return Signal(
                direction=direction,
                confidence=confidence,
                metadata={
                    "raw_action": action_val,
                    "probabilities": probs.tolist(),
                    "device": str(self.device),
                },
            )

        except Exception as e:
            self.logger.exception(f"Error during PPO prediction: {e}")
            return Signal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def save(self, path: Union[str, Path]) -> None:
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

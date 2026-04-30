"""AI/ML models: ensemble systems and neural architectures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class Signal:
    """
    Standard signal output from AI models.

    Attributes:
        direction: +1 for Buy, -1 for Sell, 0 for Hold.
        confidence: Prediction confidence score (0.0 to 1.0).
        metadata: Additional model-specific information.
    """
    direction: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Abstract base class for all AI models in the system.
    Enforces a common interface for prediction.
    """
    @abstractmethod
    def predict(self, features: Any) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input data for the model (e.g., OHLCV window).

        Returns:
            A Signal object containing the prediction.
        """
        pass


from src.models.ensemble import EnsembleModel, LSTMAttentionModel
from src.models.ppo_agent import PPOAgent
from src.models.lstm_model import LSTMModel
from src.models.dreamer_agent import DreamerAgent

__all__ = [
    "Signal",
    "BaseModel",
    "EnsembleModel",
    "LSTMAttentionModel",
    "PPOAgent",
    "LSTMModel",
    "DreamerAgent"
]

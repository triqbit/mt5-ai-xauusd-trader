"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models in the system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

@dataclass
class Signal:
    """
    Standard signal format returned by all models.
    direction: 1 (Buy), -1 (Sell), 0 (Hold)
    confidence: Probability or confidence score [0, 1]
    """
    direction: int
    confidence: float

class BaseModel(ABC):
    """
    Abstract base class for all models (PPO, LSTM, Dreamer, Ensemble).
    Ensures a consistent interface for the trading engine.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Preprocessed input features (NumPy array).

        Returns:
            Signal object containing direction and confidence.
        """
        pass

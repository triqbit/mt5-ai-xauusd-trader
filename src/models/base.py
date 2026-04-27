"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base interfaces and common data structures for all predictive models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


@dataclass
class Signal:
    """
    Standardised signal object for communication between models and the ensemble layer.
    """
    direction: int  # +1 (Buy), -1 (Sell), 0 (Hold)
    confidence: float  # Model confidence/probability (0.0 to 1.0)


class BaseModel(ABC):
    """
    Abstract base class for all predictive models.
    Ensures a consistent interface for the ensemble orchestrator.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input data for prediction (e.g., market state, indicators).

        Returns:
            Signal: The predicted direction and confidence.
        """
        pass

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base classes and data structures for all AI/ML models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """
    Standardised signal output for all models.
    direction: 1 (Buy), -1 (Sell), 0 (Hold)
    confidence: 0.0 to 1.0 probability or confidence score
    """
    direction: int
    confidence: float


class BaseModel(ABC):
    """
    Abstract Base Class for all trading models in the system.
    Ensures a consistent interface for the ensemble orchestrator.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Preprocessed feature vector or matrix (np.ndarray)

        Returns:
            Signal: Dataclass containing direction and confidence
        """
        pass

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Abstract base class for all AI/ML trading models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """
    Standardised trading signal.
    direction: +1 for Buy, -1 for Sell, 0 for Hold.
    confidence: model confidence score [0.0, 1.0].
    """

    direction: int
    confidence: float


class BaseModel(ABC):
    """
    Base interface for all trading models.
    Ensures consistent prediction API across ensemble members.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature vector or sequence (NumPy array).

        Returns:
            Signal: Standardised Signal object containing direction and confidence.
        """
        pass

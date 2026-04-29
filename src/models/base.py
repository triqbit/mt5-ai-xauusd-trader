"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Abstract base class and standard signal interface for all AI models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """
    Standardised model output.
    direction: 1 (Buy), -1 (Sell), 0 (Hold)
    confidence: float (0.0 to 1.0)
    """
    direction: int
    confidence: float


class BaseModel(ABC):
    """
    Abstract base class for all AI models in the ensemble.
    Ensures a consistent interface for the Ensemble orchestrator.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from the input features.

        Args:
            features: Preprocessed market data and indicators.

        Returns:
            Signal: Direction and confidence.
        """
        pass

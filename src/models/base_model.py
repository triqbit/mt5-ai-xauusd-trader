"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models.
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from src.core.types import Signal


class BaseModel(ABC):
    """Abstract base class for all trading models."""

    @abstractmethod
    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature array (e.g., OHLCV + technical indicators).

        Returns:
            A Signal object containing direction and confidence.
        """
        pass

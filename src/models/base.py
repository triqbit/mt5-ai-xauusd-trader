"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Abstract base classes and common data structures for ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass
class Signal:
    """
    Standardised signal output for all trading models.
    direction: 1 (Buy), -1 (Sell), 0 (Hold)
    confidence: float between 0.0 and 1.0
    """

    direction: int
    confidence: float


class BaseModel(ABC):
    """
    Abstract base class for all AI/ML models in the system.
    Enforces a consistent interface for prediction and ensemble integration.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.
        Args:
            features: Preprocessed market features (OHLCV + indicators)
        Returns:
            Signal object with direction and confidence.
        """
        pass

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base interface and data structures for all AI/ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """
    Standardized model output signal.
    direction: +1 (Buy), -1 (Sell), 0 (Hold)
    confidence: 0.0 to 1.0 probability or strength score
    """
    direction: int
    confidence: float


class BaseModel(ABC):
    """
    Abstract base class for all AI/ML models.
    Ensures consistency across different architectures (PPO, LSTM, Dreamer).
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature array (OHLCV + indicators)

        Returns:
            Signal object containing direction and confidence
        """
        pass

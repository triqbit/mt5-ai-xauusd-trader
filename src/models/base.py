"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base interfaces and common data structures for all models.
Author : triqbit
License: MIT
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """Standardized prediction output from any model."""

    direction: int  # +1 (Buy), -1 (Sell), 0 (Hold)
    confidence: float  # 0.0 to 1.0


class BaseModel(ABC):
    """Abstract base class for all predictive models."""

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature vector or sequence.

        Returns:
            Signal object.
        """
        pass

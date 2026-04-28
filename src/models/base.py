"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base classes and standard interfaces for AI models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    """Standardized model output."""

    direction: int  # 1 for Buy, -1 for Sell, 0 for Hold
    confidence: float  # 0.0 to 1.0


class BaseModel(ABC):
    """Abstract base class for all AI models."""

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal from feature vector.
        Args:
            features: np.ndarray of features.
        Returns:
            Signal object.
        """
        pass

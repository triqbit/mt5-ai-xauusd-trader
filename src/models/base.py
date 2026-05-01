"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Standardised interfaces and data structures for all AI models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np


@dataclass
class Signal:
    """
    Standardised trading signal produced by AI models.

    Attributes:
        direction: int (+1 Buy, -1 Sell, 0 Hold)
        confidence: float (0.0 to 1.0)
        metadata: dict containing model-specific details (e.g., logits, attention weights)
    """
    direction: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Abstract Base Class for all AI models in the trading system.
    Ensures consistent interface for ensemble integration and backtesting.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal based on input features.

        Args:
            features: NumPy array of preprocessed features.

        Returns:
            Signal object with direction, confidence, and metadata.
        """
        pass

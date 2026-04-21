"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Common interface for all AI/ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np


@dataclass
class Signal:
    """
    Standardized model output.
    direction: 1 for Buy, -1 for Sell, 0 for Hold.
    confidence: float between 0 and 1.
    metadata: optional dictionary for additional model-specific info.
    """

    direction: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Abstract base class for all trading models.
    Ensures a consistent interface for prediction and integration into ensembles.
    """

    @abstractmethod
    def predict(self, features: np.ndarray) -> Signal:
        """
        Generate a trading signal based on input features.

        Args:
            features: NumPy array of input data (OHLCV + indicators).

        Returns:
            A Signal object containing direction and confidence.
        """
        pass

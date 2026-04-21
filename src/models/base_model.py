"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Standardised model interface and signal definitions.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np


@dataclass
class Signal:
    """Standardised model output."""

    direction: int  # +1 buy, -1 sell, 0 hold
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.direction not in [-1, 0, 1]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} must be between 0 and 1")


class BaseModel(ABC):
    """Abstract base class for all trading models."""

    @abstractmethod
    def predict(self, features: np.ndarray, **kwargs) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Preprocessed input data (e.g., OHLCV + indicators)
            **kwargs: Additional model-specific parameters (e.g., sequence data)

        Returns:
            A Signal object containing direction and confidence.
        """
        pass

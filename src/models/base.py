"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base.py
Base classes and common interfaces for all AI models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Signal:
    """
    Standard signal output from AI models.

    Attributes:
        direction: +1 for Buy, -1 for Sell, 0 for Hold.
        confidence: Prediction confidence score (0.0 to 1.0).
        metadata: Additional model-specific information.
    """

    direction: int
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Abstract base class for all AI models in the system.
    Enforces a common interface for prediction.
    """

    @abstractmethod
    def predict(self, features: Any) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input data for the model (e.g., OHLCV window).

        Returns:
            A Signal object containing the prediction.
        """
        pass

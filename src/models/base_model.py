"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple

import numpy as np

from src.core.constants import SignalDirection


class Signal(NamedTuple):
    """Standardized model output."""

    direction: SignalDirection
    confidence: float
    metadata: dict[str, Any] | None = None


class BaseModel(ABC):
    """Abstract base class for all trading models."""

    @abstractmethod
    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature array (e.g., OHLCV + technical indicators).
            **kwargs: Additional context (seq, regime_info, etc.).

        Returns:
            A Signal object containing direction and confidence.
        """
        pass

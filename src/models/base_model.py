"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Abstract base class and standardized signal interface for all AI models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

import numpy as np


@dataclass
class Signal:
    """Standardized model output signal."""

    direction: int  # 1: Buy, -1: Sell, 0: Hold
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseModel(ABC):
    """Abstract base class for all AI/ML models."""

    @abstractmethod
    def predict(self, features: np.ndarray, **kwargs: Any) -> Signal:
        """
        Generate a trading signal from input features.

        Args:
            features: Preprocessed input features (NumPy array).
            **kwargs: Additional model-specific parameters.

        Returns:
            A Signal object.
        """
        pass

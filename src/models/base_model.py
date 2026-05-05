"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models.
"""

from abc import ABC, abstractmethod

import numpy as np

from src.core.types import TradeSignal


class BaseModel(ABC):
    """Abstract base class for all trading models."""

    @abstractmethod
    def predict(self, features: np.ndarray) -> TradeSignal:
        """
        Generate a trading signal from input features.

        Args:
            features: Input feature array (e.g., OHLCV + technical indicators).

        Returns:
            A TradeSignal object containing direction and confidence.
        """
        pass

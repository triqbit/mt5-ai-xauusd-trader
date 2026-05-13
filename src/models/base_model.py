"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field

from src.core.constants import SignalDirection


class Signal(PydanticBaseModel):
    """
    Standardized model output.
    Enforces strict range validation for confidence and type safety for direction.

    This model is immutable (frozen) to ensure that model predictions cannot be
    tampered with once generated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    direction: SignalDirection = Field(
        ..., description="The predicted trade direction: 1 (BUY), -1 (SELL), or 0 (HOLD)."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score (0.0 to 1.0). Higher means more certainty.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata or debug info from the model."
    )

    def _asdict(self) -> dict[str, Any]:
        """
        Return a dictionary representation of the signal.
        Provided for backward compatibility with NamedTuple._asdict().
        """
        return self.model_dump()


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

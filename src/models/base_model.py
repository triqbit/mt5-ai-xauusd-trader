"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/models/base_model.py
Base interface for all AI/ML models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import SignalDirection


class Signal(BaseModel):
    """
    Standardized model output schema for all trading algorithms.
    Enforces technical trust by validating confidence ranges and ensuring immutability.

    All model outputs are immutable (frozen) to preserve the integrity of the
    decision-making audit trail.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    direction: SignalDirection = Field(
        ..., description="The predicted signal direction (BUY, SELL, or HOLD)."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The model's confidence score (0.0 to 1.0). Higher means more certainty.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional diagnostic metadata or attribution details."
    )

    def _asdict(self) -> dict[str, Any]:
        """
        Backward compatibility helper for NamedTuple-style serialization.
        Deprecated: Use .model_dump() instead.
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

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/schemas.py
Centralized Pydantic schemas for data validation and technical trust.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum

from pydantic import BaseModel, Field, field_validator


class SignalDirection(IntEnum):
    """Standardized signal directions for schema enforcement."""
    BUY = 1
    SELL = -1
    HOLD = 0


class TradeSignalSchema(BaseModel):
    """
    Enterprise-grade validated trading signal schema.
    Enforces strict constraints to ensure technical trust in model outputs.
    """

    symbol: str = Field(..., description="The financial instrument symbol (e.g., XAUUSD)")
    direction: SignalDirection = Field(..., description="Signal direction: 1 (BUY), -1 (SELL), 0 (HOLD)")
    entry_price: float = Field(..., gt=0, description="The target entry price for the trade")
    stop_loss: float = Field(..., gt=0, description="The mandatory protective stop loss price")
    take_profit: float = Field(..., gt=0, description="The target profit taking price")
    lot_size: float = Field(..., ge=0.01, description="The position size in lots (minimum 0.01)")
    algorithm: str = Field(..., description="The name of the algorithm that generated this signal")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="The model's confidence score (0.0 to 1.0)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="The UTC timestamp when the signal was generated",
    )

    @field_validator("direction", mode="before")
    @classmethod
    def parse_direction(cls, v: int | SignalDirection) -> SignalDirection:
        """Ensure direction is a valid SignalDirection enum."""
        if isinstance(v, int):
            try:
                return SignalDirection(v)
            except ValueError:
                raise ValueError(f"Invalid direction: {v}. Must be 1, -1, or 0.")
        return v

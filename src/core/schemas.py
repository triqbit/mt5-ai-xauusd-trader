"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/schemas.py

Centralized Pydantic schemas for data validation and technical trust.
This module defines the core data structures used throughout the system,
ensuring strict runtime validation and price sanity checks.

Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalDirection(IntEnum):
    """Standardized signal directions for schema enforcement."""
    BUY = 1
    SELL = -1
    HOLD = 0


class TradeSignal(BaseModel):
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
            except ValueError as err:
                raise ValueError(f"Invalid direction: {v}. Must be 1, -1, or 0.") from err
        return v

    @model_validator(mode="after")
    def validate_price_boundaries(self) -> TradeSignal:
        """
        Validate that SL/TP are on the correct side of the entry price
        based on the signal direction.
        """
        if self.direction == SignalDirection.BUY:
            if self.stop_loss >= self.entry_price:
                raise ValueError(
                    f"BUY Stop Loss ({self.stop_loss}) must be below Entry Price ({self.entry_price})"
                )
            if self.take_profit <= self.entry_price:
                raise ValueError(
                    f"BUY Take Profit ({self.take_profit}) must be above Entry Price ({self.entry_price})"
                )
        elif self.direction == SignalDirection.SELL:
            if self.stop_loss <= self.entry_price:
                raise ValueError(
                    f"SELL Stop Loss ({self.stop_loss}) must be above Entry Price ({self.entry_price})"
                )
            if self.take_profit >= self.entry_price:
                raise ValueError(
                    f"SELL Take Profit ({self.take_profit}) must be below Entry Price ({self.entry_price})"
                )
        return self

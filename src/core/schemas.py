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
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.constants import SYMBOL_PATTERN, SignalDirection


class TradeSignal(BaseModel):
    """
    Enterprise-grade validated trading signal schema.
    Enforces strict constraints to ensure technical trust in model outputs.
    """

    symbol: str = Field(
        ...,
        pattern=SYMBOL_PATTERN,
        description="The financial instrument symbol (e.g., XAUUSD). Must be 3-20 uppercase alphanumeric characters.",
    )
    direction: SignalDirection = Field(
        ..., description="Signal direction: 1 (BUY), -1 (SELL), 0 (HOLD)"
    )
    entry_price: float = Field(
        ..., gt=0, description="The target entry price for the trade (must be positive)"
    )
    stop_loss: float = Field(
        ..., gt=0, description="The mandatory protective stop loss price (must be positive)"
    )
    take_profit: float = Field(
        ..., gt=0, description="The target profit taking price (must be positive)"
    )
    lot_size: float = Field(..., ge=0.01, description="The position size in lots (minimum 0.01)")
    algorithm: str = Field(..., description="The name of the algorithm that generated this signal")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The model's confidence score (0.0 to 1.0). Higher means more certainty.",
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
        based on the signal direction and enforce minimum Risk-Reward ratio.
        """
        if self.direction == SignalDirection.HOLD:
            return self

        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)

        if risk <= 0:
            raise ValueError("Risk (Entry - SL) must be greater than zero")

        rr_ratio = reward / risk
        min_rr = 1.5

        if rr_ratio < min_rr:
            raise ValueError(
                f"Risk-Reward ratio ({rr_ratio:.2f}) is below the required minimum of {min_rr}. "
                f"Risk: {risk:.2f}, Reward: {reward:.2f}"
            )

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


class ExecutionDecision(BaseModel):
    """
    Structured result of the execution filter cascade.
    Enforces technical trust by ensuring every rejection has an explicit reason.
    """

    signal: TradeSignal = Field(..., description="The trade signal being evaluated")
    is_approved: bool = Field(..., description="Final decision: True if passed all filters")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level of the signal"
    )
    blocked_by: str | None = Field(
        None, description="The name of the filter that blocked execution, if any"
    )
    trace: dict[str, Any] = Field(
        default_factory=dict, description="Detailed audit trace of all filter evaluations"
    )

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "ExecutionDecision":
        """Ensure blocked_by is populated if execution is not approved."""
        if not self.is_approved and not self.blocked_by:
            raise ValueError("A blocked decision must provide a 'blocked_by' reason.")
        return self

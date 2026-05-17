"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/schemas.py

Centralized Pydantic schemas for data validation and technical trust.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.constants import SYMBOL_PATTERN, SignalDirection


class TradeSignal(BaseModel):
    """
    Enterprise-grade validated trading signal schema.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(..., pattern=SYMBOL_PATTERN)
    direction: SignalDirection
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    lot_size: float = Field(..., ge=0.01)
    algorithm: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("direction", mode="before")
    @classmethod
    def parse_direction(cls, v: int | SignalDirection) -> SignalDirection:
        if isinstance(v, int):
            return SignalDirection(v)
        return v

    @model_validator(mode="after")
    def validate_price_boundaries(self) -> TradeSignal:
        if self.direction == SignalDirection.HOLD:
            return self

        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)

        if risk <= 0:
            raise ValueError("Risk must be greater than zero")

        rr_ratio = reward / risk
        if rr_ratio < 1.5:
            raise ValueError(f"Risk-Reward ratio ({rr_ratio:.2f}) below 1.5")

        if self.direction == SignalDirection.BUY:
            if self.stop_loss >= self.entry_price or self.take_profit <= self.entry_price:
                raise ValueError("Invalid BUY boundaries")
        elif self.direction == SignalDirection.SELL:
            if self.stop_loss <= self.entry_price or self.take_profit >= self.entry_price:
                raise ValueError("Invalid SELL boundaries")
        return self


class DailyStats(BaseModel):
    """Intraday PnL tracker."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    day: date = Field(default_factory=date.today)
    realised_pnl: float = 0.0
    trade_count: int = 0
    peak_equity: float = 0.0
    consecutive_losses: int = 0


class RiskDecision(BaseModel):
    """Decision details from the Risk Engine."""
    is_approved: bool
    reason: str = ""
    adjusted_lot_size: float = 0.0


class ExecutionDecision(BaseModel):
    """Structured result of the execution filter cascade."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    signal: TradeSignal
    is_approved: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    blocked_by: str | None = None
    trace: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "ExecutionDecision":
        if not self.is_approved and not self.blocked_by:
            raise ValueError("A blocked decision must provide a 'blocked_by' reason.")
        return self

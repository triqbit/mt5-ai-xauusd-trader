"""
src/schemas/signals.py
Pydantic schemas for trading signals.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class TradeSignalSchema(BaseModel):
    """Schema for validated trading signals."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbol: str
    direction: Literal[1, -1, 0]  # +1 buy, -1 sell, 0 hold
    entry_price: float = Field(..., gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    lot_size: float = Field(..., ge=0)
    algorithm: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_reward_ratio(self) -> float:
        if not self.stop_loss or not self.take_profit or self.entry_price == self.stop_loss:
            return 0.0
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk

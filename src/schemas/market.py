"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/schemas/market.py
Pydantic schemas for market data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class OHLCVData(BaseModel):
    """Schema for historical candle data."""
    time: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    tick_volume: int = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

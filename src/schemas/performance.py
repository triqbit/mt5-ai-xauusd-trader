"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/schemas/performance.py
Pydantic schemas for performance metrics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class PerformanceMetricsSchema(BaseModel):
    """Schema for system performance reporting."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sharpe_ratio: float = Field(default=0.0)
    profit_factor: float = Field(default=0.0)
    max_drawdown: float = Field(default=0.0)
    total_trades: int = Field(default=0, ge=0)
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)

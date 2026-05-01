"""
src/schemas/performance.py
Pydantic schemas for performance metrics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class PerformanceMetricsSchema(BaseModel):
    """Schema for backtest and live performance metrics."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    win_rate: float = Field(..., ge=0.0, le=1.0)

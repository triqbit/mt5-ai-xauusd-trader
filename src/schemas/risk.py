"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/schemas/risk.py
Pydantic schemas for risk management.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RiskParameters(BaseModel):
    """Configuration for risk management."""
    max_positions: int = Field(default=3, ge=1, le=10)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.05)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.20)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class ExecutionDecision(BaseModel):
    """Outcome of a trade signal evaluation."""
    approved: bool
    rejection_reason: Optional[str] = None
    signal_id: Optional[int] = None
    symbol: str
    direction: int

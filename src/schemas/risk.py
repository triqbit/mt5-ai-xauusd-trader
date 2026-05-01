"""
src/schemas/risk.py
Pydantic schemas for risk parameters and execution decisions.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RiskParameters(BaseModel):
    """Schema for risk configuration validation."""
    max_positions: int = Field(default=3, ge=1, le=10)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.05)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.20)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    min_risk_reward: float = Field(default=1.5, ge=1.0)


class ExecutionDecision(BaseModel):
    """Schema for execution filter results."""
    approved: bool
    rejection_reason: Optional[str] = None
    symbol: str
    direction: int
    timestamp: float

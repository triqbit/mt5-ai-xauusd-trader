"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/types.py
Centralized type definitions and data structures to ensure system-wide consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TradeSignal:
    """Validated trading signal passed to order execution."""

    symbol: str
    direction: int  # +1 buy / -1 sell
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    algorithm: str
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionDecision:
    """Result of the execution filter cascade."""

    signal: TradeSignal
    is_approved: bool
    confidence_score: float
    blocked_by: Optional[str] = None

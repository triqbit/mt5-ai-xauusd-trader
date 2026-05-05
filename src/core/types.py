"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/types.py
Centralized type definitions and fundamental trading structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any, NamedTuple


class SignalDirection(IntEnum):
    """Standardized signal directions across all models and environments."""

    BUY = 1
    SELL = -1
    HOLD = 0


class TradeSignal(NamedTuple):
    """Standardized model output / validated signal."""

    direction: SignalDirection
    confidence: float
    metadata: dict[str, Any] | None = None


@dataclass
class TradeSignalExecution:
    """
    Validated trading signal passed to order execution.
    Legacy dataclass format used by risk management and connectors.
    """

    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    algorithm: str
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

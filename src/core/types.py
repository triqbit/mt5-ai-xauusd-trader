"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/types.py
Centralized hub for core data structures and enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, NamedTuple, Optional


class SignalDirection(IntEnum):
    """Standardized signal directions across all models and environments."""

    BUY = 1
    SELL = -1
    HOLD = 0


class ModelAction(IntEnum):
    """
    Standardized categorical actions used by RL environments and model outputs.
    Mapped to SignalDirection in adapters or the execution loop.
    """

    HOLD = 0
    BUY = 1
    SELL = 2

    def to_direction(self) -> SignalDirection:
        """Map categorical action to numerical signal direction."""
        mapping = {
            ModelAction.HOLD: SignalDirection.HOLD,
            ModelAction.BUY: SignalDirection.BUY,
            ModelAction.SELL: SignalDirection.SELL,
        }
        return mapping[self]


class Signal(NamedTuple):
    """Standardized model output (pre-risk management)."""

    direction: SignalDirection
    confidence: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TradeSignal:
    """
    Validated trading signal passed to order execution (post-risk management).
    Enforces use of SignalDirection enum and UTC timestamps.
    """

    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    algorithm: str
    confidence: float  # 0.0 - 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

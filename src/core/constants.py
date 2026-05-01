"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/constants.py
Centralized constants and enums to ensure system-wide consistency.
"""

from enum import IntEnum


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

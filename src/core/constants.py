"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/constants.py
Centralized constants and enums to ensure system-wide consistency.
"""

from enum import Enum, IntEnum
from typing import Literal

# --- Validation Patterns ---
SYMBOL_PATTERN = r"^[A-Z0-9]{3,20}$"

# --- Timeframes ---
VALID_TIMEFRAMES = Literal[
    "M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
    "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "W1", "MN1"
]

VALID_TIMEFRAME_LIST = [
    "M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
    "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1", "W1", "MN1"
]


class SignalDirection(IntEnum):
    """
    Standardized signal directions across all models and environments.
    BUY (1) : Positive price expectation, trigger long entry.
    SELL (-1): Negative price expectation, trigger short entry.
    HOLD (0): Neutral or uncertain, do not enter or maintain flat.
    """

    BUY = 1
    SELL = -1
    HOLD = 0


class DecisionStatus(str, Enum):
    """
    Augmented status levels for trade execution.
    EXECUTE: High-confidence signal passing all filters and risk gates.
    CAUTION: Valid signal but with elevated risk or lower confidence; may require manual oversight or reduced sizing.
    BLOCKED: Signal rejected by risk management, execution filters, or macro intelligence.
    """

    EXECUTE = "execute"
    CAUTION = "caution"
    BLOCKED = "blocked"


class EventImpact(IntEnum):
    """Normalized event impact scores for macro events."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EventCategory(Enum):
    """Categories of macro events relevant to XAUUSD."""

    CPI = "CPI"
    NFP = "NFP"
    FOMC = "FOMC"
    RATES = "RATES"
    USD = "USD"
    USD_MACRO = "USD_MACRO"
    GEOPOLITICAL = "GEOPOLITICAL"
    OTHER = "OTHER"


class ModelAction(IntEnum):
    """
    Standardized categorical actions used by RL environments and model outputs.
    Mapped to SignalDirection in adapters or the execution loop to ensure
    consistent interpretation of model predictions.

    HOLD (0): No action recommended.
    BUY (1) : Long position recommended.
    SELL (2): Short position recommended.
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

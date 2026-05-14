"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/core/constants.py
Centralized constants and enums to ensure system-wide consistency.

This module defines the primary domain constants and enumerations used
throughout the application to ensure type safety, deterministic validation,
and clear operational semantics.
"""

from enum import Enum, IntEnum
from typing import Literal

# --- Validation Patterns ---
# Enforces institutional naming conventions for financial instruments.
SYMBOL_PATTERN = r"^[A-Z0-9]{3,20}$"

# --- Timeframes ---
# Strict Literal type for static analysis of trading intervals.
VALID_TIMEFRAMES = Literal[
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M10",
    "M12",
    "M15",
    "M20",
    "M30",
    "H1",
    "H2",
    "H3",
    "H4",
    "H6",
    "H8",
    "H12",
    "D1",
    "W1",
    "MN1",
]

# List version of timeframes for runtime membership validation.
VALID_TIMEFRAME_LIST = [
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M10",
    "M12",
    "M15",
    "M20",
    "M30",
    "H1",
    "H2",
    "H3",
    "H4",
    "H6",
    "H8",
    "H12",
    "D1",
    "W1",
    "MN1",
]


class SignalDirection(IntEnum):
    """
    Standardized signal directions across all models and environments.

    BUY (1) : Positive price expectation, triggers a long entry or maintains existing long.
    SELL (-1): Negative price expectation, triggers a short entry or maintains existing short.
    HOLD (0): Neutral or uncertain market state; do not enter new positions and typically flatten existing ones.
    """

    BUY = 1
    SELL = -1
    HOLD = 0


class DecisionStatus(str, Enum):
    """
    Augmented status levels for trade execution and operator feedback.

    EXECUTE: High-confidence signal passing all filters and risk gates. Ready for immediate execution.
    REVIEW: Signal is valid but meets criteria for manual operator oversight before execution.
    CAUTION: Valid signal but with elevated risk (e.g., high volatility) or lower confidence.
             May require manual oversight or reduced position sizing.
    BLOCKED: Signal rejected by risk management, execution filters, or macro intelligence.
             Strictly prohibited from execution.
    """

    EXECUTE = "execute"
    REVIEW = "review"
    CAUTION = "caution"
    BLOCKED = "blocked"


class EventImpact(IntEnum):
    """
    Normalized event impact scores for macroeconomic and geopolitical events.
    Higher values indicate greater potential for market volatility and slippage.

    LOW (1): Minimal expected volatility; trade normally.
    MEDIUM (2): Moderate volatility; consider reduced sizing.
    HIGH (3): Significant volatility expected; typically triggers a trading halt.
    CRITICAL (4): Extreme volatility or tail risk; mandatory trading halt and liquidation of existing positions.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class EventCategory(Enum):
    """
    Functional categories for macroeconomic events, used to apply specialized
    risk handling and duration-based cooling periods.
    """

    CPI = "CPI"  # Inflation data
    NFP = "NFP"  # Employment data
    FOMC = "FOMC"  # Federal Reserve meetings
    RATES = "RATES"  # Interest rate decisions
    USD = "USD"  # General USD macro releases
    USD_MACRO = "USD_MACRO"  # Broad US economic indicators
    GEOPOLITICAL = "GEOPOLITICAL"  # Political events, wars, or sanctions
    OTHER = "OTHER"  # Miscellaneous events


class ModelAction(IntEnum):
    """
    Standardized categorical actions used by Reinforcement Learning (RL)
    environments and model outputs.

    Mapped to SignalDirection in adapters to ensure consistent interpretation
    of model predictions across different architectures.

    HOLD (0): No action recommended (Stay flat).
    BUY (1) : Long position recommended.
    SELL (2): Short position recommended.
    """

    HOLD = 0
    BUY = 1
    SELL = 2

    def to_direction(self) -> SignalDirection:
        """
        Deterministic mapping from model action indices to domain signal directions.
        """
        mapping = {
            ModelAction.HOLD: SignalDirection.HOLD,
            ModelAction.BUY: SignalDirection.BUY,
            ModelAction.SELL: SignalDirection.SELL,
        }
        return mapping[self]

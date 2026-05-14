"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_models.py
Typed models for macroeconomic events and risk status.

These models provide a standardized interface for macroeconomic risk data.
They are immutable (frozen) to ensure that risk assessments remain consistent
throughout the decision-making pipeline.

Author : triqbit
License: MIT
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.constants import EventCategory, EventImpact


class MacroEvent(BaseModel):
    """
    Typed model for a macroeconomic or geopolitical event.
    Standardizes event data across multiple providers for institutional-grade risk analysis.

    This model is immutable (frozen) and forbids extra fields.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., description="Human-readable name of the event (e.g., 'Core CPI m/m').")
    category: EventCategory = Field(
        ..., description="Functional category for specialized risk handling."
    )
    impact: EventImpact = Field(..., description="Normalized impact score (1-4).")
    timestamp: datetime = Field(..., description="UTC start time of the event.")
    end_timestamp: datetime | None = Field(
        None, description="UTC end time. If missing, a category-based default is applied."
    )
    symbol_impact: list[str] = Field(
        default_factory=lambda: ["XAUUSD", "USD"],
        description="List of symbols or currencies directly impacted by this event.",
    )
    description: str | None = Field(None, description="Extended details or context for the event.")
    actual: float | None = Field(None, description="Actual reported value (if available).")
    forecast: float | None = Field(None, description="Consensus forecast value.")
    previous: float | None = Field(None, description="Previously reported value.")

    @property
    def is_high_impact(self) -> bool:
        """True if the event is rated HIGH or CRITICAL."""
        return self.impact >= EventImpact.HIGH

    @property
    def severity_score(self) -> float:
        """
        Normalized score (0.0 to 1.0) representing the event's severity.
        Derived from impact level and functional category.
        """
        # Base score from impact (1-4)
        base_score = float(self.impact.value) / 4.0

        # Category-based adjustment
        # Major market-moving events and geopolitical risks maintain full severity
        if self.category in [
            EventCategory.FOMC,
            EventCategory.NFP,
            EventCategory.RATES,
            EventCategory.CPI,
            EventCategory.GEOPOLITICAL,
        ]:
            category_mult = 1.0
        elif self.category in [EventCategory.USD, EventCategory.USD_MACRO]:
            category_mult = 0.9
        else:
            category_mult = 0.8

        return round(min(1.0, base_score * category_mult), 2)

    def is_ongoing(self, now: datetime) -> bool:
        """Checks if the event is currently happening (within its duration)."""
        if self.end_timestamp:
            return self.timestamp <= now <= self.end_timestamp
        return False

    @model_validator(mode="before")
    @classmethod
    def validate_and_assign_defaults(cls, data: Any) -> Any:
        """
        Ensure timestamps are timezone-aware UTC and end_timestamp is after timestamp.
        Assigns sensible default durations if end_timestamp is missing.
        """
        if not isinstance(data, dict):
            return data

        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            data["timestamp"] = ts

        ets = data.get("end_timestamp")
        if isinstance(ets, str):
            ets = datetime.fromisoformat(ets)

        if ets is None and ts is not None:
            category = data.get("category")
            # Handle string category if passed
            if isinstance(category, str):
                with contextlib.suppress(ValueError):
                    category = EventCategory(category)

            if category == EventCategory.GEOPOLITICAL:
                duration = timedelta(hours=24)
            elif category in [EventCategory.FOMC, EventCategory.RATES]:
                duration = timedelta(hours=4)
            else:
                duration = timedelta(hours=1)
            data["end_timestamp"] = ts + duration
        elif isinstance(ets, datetime):
            if ets.tzinfo is None:
                ets = ets.replace(tzinfo=UTC)
            data["end_timestamp"] = ets

        if (
            data.get("end_timestamp")
            and data.get("timestamp")
            and data["end_timestamp"] <= data["timestamp"]
        ):
            raise ValueError(
                f"end_timestamp ({data['end_timestamp']}) must be after timestamp ({data['timestamp']})"
            )

        return data


class RiskStatus(BaseModel):
    """
    Consolidated risk state derived from current macroeconomic activity.
    Used by execution filters and capital allocators to modulate trading activity.

    This model is immutable (frozen) and forbids extra fields.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_blocked: bool = Field(
        False, description="Binary flag indicating if execution is strictly prohibited."
    )
    risk_multiplier: float = Field(
        1.0, ge=0.0, le=1.0, description="Sizing multiplier (0.0 to 1.0) to scale risk exposure."
    )
    active_events: list[MacroEvent] = Field(
        default_factory=list,
        description="List of events currently in their active or cooldown window.",
    )
    blocking_events: list[MacroEvent] = Field(
        default_factory=list,
        description="List of events specifically triggering an execution block.",
    )
    reason: str | None = Field(None, description="Human-readable explanation for the risk state.")

    @model_validator(mode="before")
    @classmethod
    def validate_block_consistency(cls, data: Any) -> Any:
        """
        Enforce technical trust: if is_blocked is True, risk_multiplier must be 0.0.
        Also ensures a reason is provided if blocked.
        """
        if not isinstance(data, dict):
            return data

        if data.get("is_blocked"):
            if data.get("risk_multiplier", 1.0) > 0.0:
                data["risk_multiplier"] = 0.0
            if not data.get("reason"):
                raise ValueError("A blocked risk status must provide a reason.")
        return data

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_models.py
Typed models for macroeconomic events and risk status.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, model_validator

from src.core.constants import EventCategory, EventImpact


class MacroEvent(BaseModel):
    """
    Typed model for a macroeconomic or geopolitical event.
    Standardizes event data across multiple providers for institutional-grade risk analysis.
    """

    name: str = Field(..., description="Human-readable name of the event (e.g., 'Core CPI m/m').")
    category: EventCategory = Field(..., description="Functional category for specialized risk handling.")
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

    def is_ongoing(self, now: datetime) -> bool:
        """Checks if the event is currently happening (within its duration)."""
        if self.end_timestamp:
            return self.timestamp <= now <= self.end_timestamp
        return False

    @model_validator(mode="after")
    def validate_timestamps(self) -> MacroEvent:
        """
        Ensure timestamps are timezone-aware UTC and end_timestamp is after timestamp.
        Assigns sensible default durations if end_timestamp is missing.
        """
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

        if self.end_timestamp is None:
            # Category-based default durations
            if self.category == EventCategory.GEOPOLITICAL:
                # Geopolitical events usually have longer tail risks
                duration = timedelta(hours=24)
            elif self.category in [EventCategory.FOMC, EventCategory.RATES]:
                # Central bank events have extended impact
                duration = timedelta(hours=4)
            else:
                # Default duration for standard macro releases
                duration = timedelta(hours=1)
            self.end_timestamp = self.timestamp + duration
        elif self.end_timestamp.tzinfo is None:
            self.end_timestamp = self.end_timestamp.replace(tzinfo=UTC)

        if self.end_timestamp <= self.timestamp:
            raise ValueError(
                f"end_timestamp ({self.end_timestamp}) must be after timestamp ({self.timestamp})"
            )

        return self


class RiskStatus(BaseModel):
    """
    Consolidated risk state derived from current macroeconomic activity.
    Used by execution filters and capital allocators to modulate trading activity.
    """

    is_blocked: bool = Field(
        False, description="Binary flag indicating if execution is strictly prohibited."
    )
    risk_multiplier: float = Field(
        1.0, ge=0.0, le=1.0, description="Sizing multiplier (0.0 to 1.0) to scale risk exposure."
    )
    active_events: list[MacroEvent] = Field(
        default_factory=list, description="List of events currently in their active or cooldown window."
    )
    blocking_events: list[MacroEvent] = Field(
        default_factory=list, description="List of events specifically triggering an execution block."
    )
    reason: str | None = Field(None, description="Human-readable explanation for the risk state.")

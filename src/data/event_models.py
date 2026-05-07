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
    """Typed model for a macroeconomic event."""

    name: str
    category: EventCategory
    impact: EventImpact
    timestamp: datetime
    end_timestamp: datetime | None = None
    symbol_impact: list[str] = Field(default_factory=lambda: ["XAUUSD", "USD"])
    description: str | None = None
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None

    @property
    def is_high_impact(self) -> bool:
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
        Assigns a default duration of 1 hour if end_timestamp is missing.
        """
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

        if self.end_timestamp is None:
            # Default duration of 60 minutes if not provided
            self.end_timestamp = self.timestamp + timedelta(minutes=60)
        elif self.end_timestamp.tzinfo is None:
            self.end_timestamp = self.end_timestamp.replace(tzinfo=UTC)

        if self.end_timestamp <= self.timestamp:
            raise ValueError(f"end_timestamp ({self.end_timestamp}) must be after timestamp ({self.timestamp})")

        return self


class RiskStatus(BaseModel):
    """Current risk status based on events."""

    is_blocked: bool = False
    risk_multiplier: float = 1.0  # 1.0 = normal risk, < 1.0 = reduced risk
    active_events: list[MacroEvent] = Field(default_factory=list)
    blocking_events: list[MacroEvent] = Field(default_factory=list)
    reason: str | None = None

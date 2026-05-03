"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Ingests and normalizes high-impact macroeconomic events relevant to XAUUSD.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum, IntEnum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventImpact(IntEnum):
    """Normalized event impact scores."""

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
    USD = "USD_MACRO"
    GEOPOLITICAL = "GEOPOLITICAL"
    OTHER = "OTHER"


class MacroEvent(BaseModel):
    """Typed model for a macroeconomic event."""

    name: str
    category: EventCategory
    impact: EventImpact
    timestamp: datetime
    symbol_impact: List[str] = Field(default_factory=lambda: ["XAUUSD", "USD"])
    description: Optional[str] = None
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None

    @property
    def is_high_impact(self) -> bool:
        return self.impact >= EventImpact.HIGH


class RiskStatus(BaseModel):
    """Current risk status based on events."""

    is_blocked: bool = False
    risk_multiplier: float = 1.0  # 1.0 = normal risk, < 1.0 = reduced risk
    active_events: List[MacroEvent] = Field(default_factory=list)
    reason: Optional[str] = None


class BaseEventProvider(ABC):
    """Abstract base class for event data providers."""

    @abstractmethod
    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> List[MacroEvent]:
        """Fetch events within a time range."""
        pass


class MockEventProvider(BaseEventProvider):
    """Mock provider for testing and fallback."""

    def __init__(self, mock_events: Optional[List[MacroEvent]] = None):
        self.events = mock_events or []

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> List[MacroEvent]:
        return [e for e in self.events if start_time <= e.timestamp <= end_time]


class EventIntelligence:
    """
    Analyzes macro events to determine trading risk windows.
    Supports pre-event blocking and post-event cooldowns.
    """

    def __init__(
        self,
        provider: BaseEventProvider,
        pre_event_minutes: Optional[Dict[EventImpact, int]] = None,
        post_event_minutes: Optional[Dict[EventImpact, int]] = None,
    ):
        self.provider = provider
        # Default risk windows (minutes)
        self.pre_event_minutes = pre_event_minutes or {
            EventImpact.LOW: 5,
            EventImpact.MEDIUM: 15,
            EventImpact.HIGH: 60,
            EventImpact.CRITICAL: 120,
        }
        self.post_event_minutes = post_event_minutes or {
            EventImpact.LOW: 5,
            EventImpact.MEDIUM: 30,
            EventImpact.HIGH: 120,
            EventImpact.CRITICAL: 240,
        }

    def get_risk_status(self, current_time: Optional[datetime] = None) -> RiskStatus:
        """
        Calculates the current risk status based on upcoming and recent events.
        """
        now = current_time or datetime.now(timezone.utc)

        # Look ahead and behind based on max windows
        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())

        start_lookback = now - timedelta(minutes=max_post)
        end_lookahead = now + timedelta(minutes=max_pre)

        try:
            events = self.provider.get_upcoming_events(start_lookback, end_lookahead)
        except Exception as e:
            logger.error("Failed to fetch macro events: %s. Falling back to safe mode.", e)
            # Enterprise fallback: if we can't get data, we might want to be cautious or proceed with warning.
            # Here we proceed but log the error.
            return RiskStatus(reason="Event data unavailable")

        active_events = []
        is_blocked = False
        min_multiplier = 1.0

        for event in events:
            pre_window = self.pre_event_minutes.get(event.impact, 0)
            post_window = self.post_event_minutes.get(event.impact, 0)

            in_pre_window = event.timestamp > now and (event.timestamp - now) <= timedelta(
                minutes=pre_window
            )
            in_post_window = event.timestamp <= now and (now - event.timestamp) <= timedelta(
                minutes=post_window
            )

            if in_pre_window or in_post_window:
                active_events.append(event)

                # Logic for blocking or scaling risk
                if event.impact == EventImpact.CRITICAL:
                    is_blocked = True
                    min_multiplier = 0.0
                elif event.impact == EventImpact.HIGH:
                    # High impact might block just before/after, or reduce size
                    if in_pre_window and (event.timestamp - now) <= timedelta(minutes=30):
                        is_blocked = True
                    min_multiplier = min(min_multiplier, 0.5)
                elif event.impact == EventImpact.MEDIUM:
                    min_multiplier = min(min_multiplier, 0.75)

        reason = None
        if is_blocked:
            reason = f"Blocked by active events: {[e.name for e in active_events]}"
        elif active_events:
            reason = f"Risk reduced by active events: {[e.name for e in active_events]}"

        return RiskStatus(
            is_blocked=is_blocked,
            risk_multiplier=min_multiplier,
            active_events=active_events,
            reason=reason,
        )

    def should_block_execution(self, current_time: Optional[datetime] = None) -> bool:
        """Helper to check if execution should be blocked."""
        return self.get_risk_status(current_time).is_blocked

    def get_risk_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """Helper to get the current risk multiplier."""
        return self.get_risk_status(current_time).risk_multiplier

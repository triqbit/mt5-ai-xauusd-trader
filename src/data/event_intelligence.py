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
from datetime import datetime, timedelta
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
    USD = "USD"
    USD_MACRO = "USD_MACRO"
    GEOPOLITICAL = "GEOPOLITICAL"
    OTHER = "OTHER"


class MacroEvent(BaseModel):
    """Typed model for a macroeconomic event."""

    name: str
    category: EventCategory
    impact: EventImpact
    timestamp: datetime
    end_timestamp: Optional[datetime] = None
    symbol_impact: List[str] = Field(default_factory=lambda: ["XAUUSD", "USD"])
    description: Optional[str] = None
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None

    @property
    def is_high_impact(self) -> bool:
        return self.impact >= EventImpact.HIGH

    def is_ongoing(self, now: datetime) -> bool:
        """Checks if the event is currently happening (within its duration)."""
        if self.end_timestamp:
            return self.timestamp <= now <= self.end_timestamp
        return False


class RiskStatus(BaseModel):
    """Current risk status based on events."""

    is_blocked: bool = False
    risk_multiplier: float = 1.0  # 1.0 = normal risk, < 1.0 = reduced risk
    active_events: List[MacroEvent] = Field(default_factory=list)
    blocking_events: List[MacroEvent] = Field(default_factory=list)
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
        return [
            e
            for e in self.events
            if (e.end_timestamp or e.timestamp) >= start_time and e.timestamp <= end_time
        ]


class JSONEventProvider(BaseEventProvider):
    """Provider that reads events from a local JSON file."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> List[MacroEvent]:
        import json
        import os

        if not os.path.exists(self.file_path):
            logger.warning(f"Event file {self.file_path} not found.")
            return []

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)

            events = []
            for item in data:
                event = MacroEvent(**item)
                if (
                    event.end_timestamp or event.timestamp
                ) >= start_time and event.timestamp <= end_time:
                    events.append(event)
            return events
        except Exception as e:
            logger.error(f"Error reading JSON events: {e}")
            return []


class MetaAPIEventProvider(BaseEventProvider):
    """
    Provider that fetches macroeconomic events from MetaAPI.
    Requires metaapi-cloud-sdk.
    """

    def __init__(self, token: str):
        self.token = token
        self._impact_map = {
            "low": EventImpact.LOW,
            "medium": EventImpact.MEDIUM,
            "high": EventImpact.HIGH,
        }

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> List[MacroEvent]:
        """
        Fetches events via MetaAPI's REST interface.
        Note: This is a simplified implementation for the example.
        """
        import requests

        url = "https://calendar.metaapi.cloud/events"
        params = {
            "startTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        headers = {"auth-token": self.token}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            macro_events = []
            for item in data:
                # Basic normalization
                name = item.get("event", "Unknown Event")
                category = self._guess_category(name)
                impact_str = item.get("impact", "low").lower()
                impact = self._impact_map.get(impact_str, EventImpact.LOW)

                # MetaAPI uses UTC ISO strings
                ts = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))

                macro_events.append(
                    MacroEvent(
                        name=name,
                        category=category,
                        impact=impact,
                        timestamp=ts.replace(
                            tzinfo=None
                        ),  # Keep internal datetimes naive UTC for consistency
                    )
                )
            return macro_events

        except Exception as e:
            logger.error(f"MetaAPI event fetch failed: {e}")
            return []

    def _guess_category(self, name: str) -> EventCategory:
        name_upper = name.upper()
        if "CPI" in name_upper or "INFLATION" in name_upper:
            return EventCategory.CPI
        if "NON-FARM PAYROLL" in name_upper or "NFP" in name_upper:
            return EventCategory.NFP
        if "FOMC" in name_upper or "FED" in name_upper:
            return EventCategory.FOMC
        if "RATE" in name_upper and "DECISION" in name_upper:
            return EventCategory.RATES
        if "USD" in name_upper:
            return EventCategory.USD
        return EventCategory.OTHER


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
        now = current_time or datetime.utcnow()

        # Look ahead and behind based on max windows
        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())

        # Extend windows for long-duration events
        start_lookback = now - timedelta(minutes=max_post + 1440)  # +1 day for long events
        end_lookahead = now + timedelta(minutes=max_pre + 1440)

        try:
            events = self.provider.get_upcoming_events(start_lookback, end_lookahead)
        except Exception as e:
            logger.error("Failed to fetch macro events: %s. Falling back to safe mode.", e)
            # Enterprise fallback: if we can't get data, we return a status indicating unavailability.
            # Upstream components can decide whether to block or allow based on this.
            return RiskStatus(
                is_blocked=False, risk_multiplier=1.0, reason="Event data unavailable"
            )

        active_events = []
        blocking_events = []
        is_blocked = False
        min_multiplier = 1.0

        for event in events:
            pre_window = self.pre_event_minutes.get(event.impact, 0)
            post_window = self.post_event_minutes.get(event.impact, 0)

            # Adjust windows based on category
            if event.category in [EventCategory.FOMC, EventCategory.NFP, EventCategory.RATES]:
                pre_window = max(pre_window, 120)  # At least 2 hours for major events
                post_window = max(post_window, 180)  # At least 3 hours for major events

            is_active = False
            is_event_blocking = False

            # Check if event is ongoing
            if event.is_ongoing(now):
                is_active = True
                if event.impact >= EventImpact.HIGH:
                    is_event_blocking = True

            # Check pre-event window
            elif event.timestamp > now and (event.timestamp - now) <= timedelta(minutes=pre_window):
                is_active = True
                # Stricter blocking for HIGH impact major events
                if (
                    event.impact == EventImpact.CRITICAL
                    or (
                        event.impact == EventImpact.HIGH
                        and event.category
                        in [
                            EventCategory.FOMC,
                            EventCategory.NFP,
                            EventCategory.RATES,
                        ]
                        and (event.timestamp - now) <= timedelta(minutes=60)
                    )
                    or (
                        event.impact == EventImpact.HIGH
                        and (event.timestamp - now) <= timedelta(minutes=30)
                    )
                ):
                    is_event_blocking = True

            # Check post-event window
            elif (event.end_timestamp or event.timestamp) <= now and (
                now - (event.end_timestamp or event.timestamp)
            ) <= timedelta(minutes=post_window):
                is_active = True
                # Critical events always block during cooldown
                if event.impact == EventImpact.CRITICAL or (
                    event.impact == EventImpact.HIGH
                    and event.category
                    in [
                        EventCategory.FOMC,
                        EventCategory.NFP,
                        EventCategory.RATES,
                    ]
                    and (now - (event.end_timestamp or event.timestamp)) <= timedelta(minutes=60)
                ):
                    is_event_blocking = True

            if is_active:
                active_events.append(event)
                if is_event_blocking:
                    is_blocked = True
                    blocking_events.append(event)

                # Update multiplier
                if event.impact == EventImpact.CRITICAL:
                    min_multiplier = 0.0
                elif event.impact == EventImpact.HIGH:
                    min_multiplier = min(min_multiplier, 0.5)
                elif event.impact == EventImpact.MEDIUM:
                    min_multiplier = min(min_multiplier, 0.75)

        reason = None
        if is_blocked:
            reason = f"Blocked by active events: {[e.name for e in blocking_events]}"
        elif active_events:
            reason = f"Risk reduced by active events: {[e.name for e in active_events]}"

        return RiskStatus(
            is_blocked=is_blocked,
            risk_multiplier=min_multiplier,
            active_events=active_events,
            blocking_events=blocking_events,
            reason=reason,
        )

    def should_block_execution(self, current_time: Optional[datetime] = None) -> bool:
        """Helper to check if execution should be blocked."""
        return self.get_risk_status(current_time).is_blocked

    def get_risk_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """Helper to get the current risk multiplier."""
        return self.get_risk_status(current_time).risk_multiplier

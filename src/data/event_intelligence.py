"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Macroeconomic intelligence system for XAUUSD.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MacroEvent(BaseModel):
    """Data model for a macroeconomic event."""
    name: str
    impact: EventImpact
    symbol: str  # e.g., "USD", "ALL", "XAU"
    timestamp: datetime
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None


class EventIntelligence:
    """
    Ingests and normalises macro events to provide risk awareness.
    Supports CPI, NFP, FOMC, rate decisions, etc.
    """

    def __init__(self) -> None:
        self.events: List[MacroEvent] = []
        self._last_update: Optional[datetime] = None

    def add_event(self, event: MacroEvent) -> None:
        """Manually add an event to the intelligence system."""
        self.events.append(event)
        self.events.sort(key=lambda x: x.timestamp)

    def fetch_events(self) -> bool:
        """
        Placeholder for fetching events from external feeds (e.g., ForexFactory, MetaAPI).
        Returns True if successful, False otherwise.
        """
        # In a real implementation, this would call an API.
        # For now, we rely on manual injection or pre-populated mocks.
        logger.debug("Event fetch called - using internal event cache.")
        self._last_update = datetime.now(timezone.utc)
        return True

    def get_upcoming_events(self, window_minutes: int = 60) -> List[MacroEvent]:
        """Returns events scheduled within the next N minutes."""
        now = datetime.now(timezone.utc)
        future_limit = now + timedelta(minutes=window_minutes)
        return [e for e in self.events if now <= e.timestamp <= future_limit]

    def get_active_risk_impact(
        self,
        pre_window_high: int = 30,
        post_window_high: int = 30,
        pre_window_med: int = 15,
        post_window_med: int = 15
    ) -> EventImpact:
        """
        Determines the current highest risk impact based on active event windows.
        """
        now = datetime.now(timezone.utc)
        highest_impact = EventImpact.LOW

        for event in self.events:
            pre_window = pre_window_high if event.impact == EventImpact.HIGH else pre_window_med
            post_window = post_window_high if event.impact == EventImpact.HIGH else post_window_med

            start_time = event.timestamp - timedelta(minutes=pre_window)
            end_time = event.timestamp + timedelta(minutes=post_window)

            if start_time <= now <= end_time:
                if event.impact == EventImpact.HIGH:
                    return EventImpact.HIGH
                if event.impact == EventImpact.MEDIUM:
                    highest_impact = EventImpact.MEDIUM

        return highest_impact

    def is_execution_blocked(self, high_impact_pre: int = 30, high_impact_post: int = 30) -> bool:
        """
        Returns True if a high-impact event window is currently active.
        """
        impact = self.get_active_risk_impact(pre_window_high=high_impact_pre, post_window_high=high_impact_post)
        return impact == EventImpact.HIGH

    def get_risk_multiplier(
        self,
        high_impact_pre: int = 30,
        high_impact_post: int = 30,
        med_impact_pre: int = 15,
        med_impact_post: int = 15,
    ) -> float:
        """
        Returns a risk multiplier based on current event impact.
        HIGH -> 0.0 (blocked)
        MEDIUM -> 0.5 (half size)
        LOW -> 1.0 (normal)
        """
        impact = self.get_active_risk_impact(
            pre_window_high=high_impact_pre,
            post_window_high=high_impact_post,
            pre_window_med=med_impact_pre,
            post_window_med=med_impact_post,
        )
        if impact == EventImpact.HIGH:
            return 0.0
        if impact == EventImpact.MEDIUM:
            return 0.5
        return 1.0

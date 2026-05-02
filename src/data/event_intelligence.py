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

import httpx
from pydantic import BaseModel

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

    def __init__(
        self, feed_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    ) -> None:
        self.events: List[MacroEvent] = []
        self._last_update: Optional[datetime] = None
        self.feed_url = feed_url

    def add_event(self, event: MacroEvent) -> None:
        """Manually add an event to the intelligence system."""
        self.events.append(event)
        self.events.sort(key=lambda x: x.timestamp)

    def fetch_events(self) -> bool:
        """
        Fetches events from external feeds.
        Returns True if successful, False otherwise.
        """
        try:
            response = httpx.get(self.feed_url, timeout=10.0)
            response.raise_for_status()
            raw_events = response.json()
            self._normalize_events(raw_events)
            self._last_update = datetime.now(timezone.utc)
            logger.info("Macro events fetched and normalized | count=%d", len(self.events))
            return True
        except Exception as exc:
            logger.error("Failed to fetch macro events: %s", exc)
            return False

    def _normalize_events(self, raw_data: List[dict]) -> None:
        """Normalises raw feed data into MacroEvent models."""
        normalized = []
        for item in raw_data:
            try:
                # Basic normalization for ForexFactory-style JSON
                impact_map = {
                    "Low": EventImpact.LOW,
                    "Medium": EventImpact.MEDIUM,
                    "High": EventImpact.HIGH,
                }

                # Parse timestamp - format: "2024-05-02T08:30:00-04:00"
                # Some feeds might use different formats; handle robustly
                ts_str = item.get("date")
                if not ts_str:
                    continue

                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)

                event = MacroEvent(
                    name=item.get("title", "Unknown"),
                    impact=impact_map.get(item.get("impact"), EventImpact.LOW),
                    symbol=item.get("country", "ALL"),
                    timestamp=timestamp,
                    actual=self._parse_float(item.get("actual")),
                    forecast=self._parse_float(item.get("forecast")),
                    previous=self._parse_float(item.get("previous")),
                )
                normalized.append(event)
            except Exception as exc:
                logger.warning("Skipping malformed event data: %s | data=%s", exc, item)

        self.events = sorted(normalized, key=lambda x: x.timestamp)

    def _parse_float(self, value: Optional[str]) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            # Strip non-numeric characters like %, K, M
            clean_val = "".join(c for c in value if c.isdigit() or c in ".-")
            return float(clean_val)
        except ValueError:
            return None

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
        post_window_med: int = 15,
        target_symbol: str = "USD",
    ) -> EventImpact:
        """
        Determines the current highest risk impact based on active event windows.
        Only considers events relevant to the target symbol or gold (XAU).
        """
        now = datetime.now(timezone.utc)
        highest_impact = EventImpact.LOW
        relevant_symbols = {target_symbol, "ALL", "XAU"}

        for event in self.events:
            if event.symbol not in relevant_symbols:
                continue

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
        impact = self.get_active_risk_impact(
            pre_window_high=high_impact_pre, post_window_high=high_impact_post
        )
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

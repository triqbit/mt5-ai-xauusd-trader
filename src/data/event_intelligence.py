"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Macroeconomic event intelligence engine for XAUUSD.
Handles ingestion, severity scoring, and risk window management.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventSeverity(IntEnum):
    """Macro event impact severity level."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class MacroEvent(BaseModel):
    """Typed model for macroeconomic and geopolitical events."""

    name: str
    symbol: str  # e.g., "USD", "XAUUSD", "ALL"
    timestamp: datetime
    severity: EventSeverity
    impact_description: str
    pre_event_window_mins: int = Field(default=60, ge=0)
    post_event_window_mins: int = Field(default=120, ge=0)
    is_geopolitical: bool = False

    @property
    def is_active(self) -> bool:
        """Check if current time is within the event's risk window."""
        now = datetime.now(timezone.utc)
        start_risk = self.timestamp - timedelta(minutes=self.pre_event_window_mins)
        end_risk = self.timestamp + timedelta(minutes=self.post_event_window_mins)
        return start_risk <= now <= end_risk

    @property
    def is_imminent(self) -> bool:
        """Check if the event is about to happen (pre-event window)."""
        now = datetime.now(timezone.utc)
        start_risk = self.timestamp - timedelta(minutes=self.pre_event_window_mins)
        return start_risk <= now <= self.timestamp


class EventIntelligence:
    """
    Ingests and normalizes high-impact macroeconomic events.
    Provides risk awareness for the trading system.
    """

    def __init__(self) -> None:
        self._events: List[MacroEvent] = []
        self._last_fetch: Optional[datetime] = None
        self._fallback_mode: bool = False

    def fetch_events(self) -> bool:
        """
        Fetch events from external feeds.
        Currently implements a mocked feed for enterprise-safe testing.
        In production, this would connect to Economic Calendar APIs.
        """
        try:
            # Simulated external feed logic
            self._events = self._get_mocked_events()
            self._last_fetch = datetime.now(timezone.utc)
            self._fallback_mode = False
            logger.info("Macro events fetched successfully | count=%d", len(self._events))
            return True
        except Exception as exc:
            logger.error("Failed to fetch macro events: %s", exc)
            self._fallback_mode = True
            return False

    def get_active_events(self) -> List[MacroEvent]:
        """Return all events currently in their risk window."""
        return [e for e in self._events if e.is_active]

    def should_block_execution(self) -> bool:
        """
        Return True if a high-impact event is active and trading should be blocked.
        Enterprise-safe: If in fallback mode, we don't block unless we have cached events.
        """
        active_events = self.get_active_events()
        # Block if any high or critical event is active
        block = any(e.severity >= EventSeverity.HIGH for e in active_events)
        if block:
            event_names = [e.name for e in active_events if e.severity >= EventSeverity.HIGH]
            logger.warning("Execution BLOCKED due to macro events: %s", event_names)
        return block

    def get_risk_multiplier(self) -> float:
        """
        Calculate position size multiplier based on active events.
        - CRITICAL: 0.0 (Stop trading)
        - HIGH: 0.25 (Reduce size significantly)
        - MEDIUM: 0.5 (Reduce size)
        - LOW/NONE: 1.0 (Standard size)
        """
        active_events = self.get_active_events()
        if not active_events:
            return 1.0

        max_severity = max(e.severity for e in active_events)
        if max_severity == EventSeverity.CRITICAL:
            return 0.0
        if max_severity == EventSeverity.HIGH:
            return 0.25
        if max_severity == EventSeverity.MEDIUM:
            return 0.5
        return 0.75

    def _get_mocked_events(self) -> List[MacroEvent]:
        """Generate a set of mock events for testing and demonstration."""
        now = datetime.now(timezone.utc)
        return [
            MacroEvent(
                name="FOMC Rate Decision",
                symbol="USD",
                timestamp=now + timedelta(hours=1),
                severity=EventSeverity.CRITICAL,
                impact_description="Fed interest rate decision and press conference.",
                pre_event_window_mins=120,
                post_event_window_mins=240,
            ),
            MacroEvent(
                name="Non-Farm Payrolls (NFP)",
                symbol="USD",
                timestamp=now + timedelta(days=1),
                severity=EventSeverity.HIGH,
                impact_description="US employment data, high XAUUSD volatility.",
                pre_event_window_mins=60,
                post_event_window_mins=120,
            ),
            MacroEvent(
                name="US Consumer Price Index (CPI)",
                symbol="USD",
                timestamp=now + timedelta(hours=5),
                severity=EventSeverity.HIGH,
                impact_description="Inflation data impacting USD and Gold.",
            ),
            MacroEvent(
                name="Geopolitical Risk: Middle East Escalation",
                symbol="ALL",
                timestamp=now - timedelta(minutes=30),
                severity=EventSeverity.MEDIUM,
                impact_description="General geopolitical tension increasing safe-haven demand.",
                is_geopolitical=True,
                pre_event_window_mins=0,
                post_event_window_mins=1440,
            ),
        ]


__all__ = ["EventIntelligence", "EventSeverity", "MacroEvent"]

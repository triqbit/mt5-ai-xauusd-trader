"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Ingests and normalizes high-impact macroeconomic events relevant to XAUUSD.
Provides risk window analysis and execution hooks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventImpact(str, Enum):
    """Macroeconomic event impact levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    def _order_val(self) -> int:
        return {
            EventImpact.LOW: 0,
            EventImpact.MEDIUM: 1,
            EventImpact.HIGH: 2,
            EventImpact.CRITICAL: 3,
        }[self]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EventImpact):
            return NotImplemented
        return self._order_val() < other._order_val()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, EventImpact):
            return NotImplemented
        return self._order_val() <= other._order_val()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, EventImpact):
            return NotImplemented
        return self._order_val() > other._order_val()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, EventImpact):
            return NotImplemented
        return self._order_val() >= other._order_val()


class MacroEvent(BaseModel):
    """Typed model for a macroeconomic event."""

    name: str
    symbol: str = Field(..., description="Currency or asset affected (e.g., USD, XAU, ALL)")
    impact: EventImpact
    timestamp: datetime
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    is_geopolitical: bool = False


class EventIntelligence:
    """
    Analyzes macroeconomic events to provide risk-aware trading guidance.
    Tracks pre-event risk windows and post-event cooldown periods.
    """

    def __init__(self) -> None:
        self.events: List[MacroEvent] = []
        # Pre-event risk windows (minutes before event)
        self.pre_event_minutes = {
            EventImpact.LOW: 5,
            EventImpact.MEDIUM: 15,
            EventImpact.HIGH: 30,
            EventImpact.CRITICAL: 60,
        }
        # Post-event cooldown windows (minutes after event)
        self.post_event_minutes = {
            EventImpact.LOW: 5,
            EventImpact.MEDIUM: 30,
            EventImpact.HIGH: 60,
            EventImpact.CRITICAL: 120,
        }

    def refresh_events(self, events: List[MacroEvent]) -> None:
        """Update the internal event list and sort by timestamp."""
        self.events = sorted(events, key=lambda x: x.timestamp)
        logger.info("Refreshed event intelligence with %d events", len(self.events))

    def get_active_events(self, current_time: Optional[datetime] = None) -> List[MacroEvent]:
        """Returns events whose risk window is currently active."""
        now = current_time or datetime.utcnow()
        active = []
        for event in self.events:
            pre_window = timedelta(minutes=self.pre_event_minutes.get(event.impact, 0))
            post_window = timedelta(minutes=self.post_event_minutes.get(event.impact, 0))

            if (event.timestamp - pre_window) <= now <= (event.timestamp + post_window):
                active.append(event)
        return active

    def get_risk_multiplier(self, symbol: str, current_time: Optional[datetime] = None) -> float:
        """
        Returns a position size multiplier based on active macro risk.
        1.0 = No risk, 0.0 = Block trading.
        """
        now = current_time or datetime.utcnow()
        active_events = self.get_active_events(now)

        # Filter for relevant events (USD, XAU, or global/geopolitical)
        relevant = [
            e for e in active_events
            if e.symbol in ("USD", "XAU", "ALL") or e.symbol == symbol or e.is_geopolitical
        ]

        if not relevant:
            return 1.0

        # Determine the highest impact among active relevant events
        max_impact = max(e.impact for e in relevant)

        multipliers = {
            EventImpact.LOW: 0.9,
            EventImpact.MEDIUM: 0.75,
            EventImpact.HIGH: 0.5,
            EventImpact.CRITICAL: 0.0,
        }

        multiplier = multipliers.get(max_impact, 1.0)
        logger.debug("Macro risk multiplier: %.2f (due to %d events)", multiplier, len(relevant))
        return multiplier

    def is_trading_blocked(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """Returns True if high-impact events warrant a total execution block."""
        return self.get_risk_multiplier(symbol, current_time) <= 0.0


class MockEventProvider:
    """Provides mock macroeconomic data for testing and fallbacks."""

    @staticmethod
    def get_upcoming_events() -> List[MacroEvent]:
        """Generates a set of realistic mock events relative to current time."""
        now = datetime.utcnow()
        return [
            MacroEvent(
                name="CPI m/m",
                symbol="USD",
                impact=EventImpact.HIGH,
                timestamp=now + timedelta(minutes=45),
            ),
            MacroEvent(
                name="Non-Farm Payrolls",
                symbol="USD",
                impact=EventImpact.CRITICAL,
                timestamp=now + timedelta(hours=2),
            ),
            MacroEvent(
                name="FOMC Interest Rate Decision",
                symbol="USD",
                impact=EventImpact.CRITICAL,
                timestamp=now + timedelta(days=1),
            ),
            MacroEvent(
                name="Geopolitical Tension Spike",
                symbol="ALL",
                impact=EventImpact.MEDIUM,
                timestamp=now - timedelta(minutes=10),
                is_geopolitical=True,
            ),
        ]

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Ingest and normalize high-impact macroeconomic events relevant to XAUUSD.
Author : triqbit
License: MIT
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from src.core.config import TradingConfig

logger = logging.getLogger(__name__)


class EventImpact(str, Enum):
    """Macro event impact levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MacroEvent(BaseModel):
    """Typed model for macroeconomic events."""

    name: str
    symbol: str  # e.g., 'USD', 'XAUUSD', 'ALL'
    impact: EventImpact
    timestamp: datetime
    pre_window_mins: int = 30
    post_window_mins: int = 60

    @property
    def start_time(self) -> datetime:
        return self.timestamp - timedelta(minutes=self.pre_window_mins)

    @property
    def end_time(self) -> datetime:
        return self.timestamp + timedelta(minutes=self.post_window_mins)

    def is_active(self, current_time: datetime) -> bool:
        return self.start_time <= current_time <= self.end_time


class EventIntelligence:
    """
    Orchestrates macroeconomic event awareness.
    Provides logic for blocking execution or reducing risk during volatile windows.
    """

    def __init__(self, config: Optional[TradingConfig] = None) -> None:
        self.cfg = config
        self.events: List[MacroEvent] = []
        self._last_fetch: Optional[datetime] = None
        logger.info("EventIntelligence initialized")

    def fetch_events(self) -> List[MacroEvent]:
        """
        Mock implementation of external event feed.
        In production, this would call an API like ForexFactory, Bloomberg, or AlphaVantage.
        """
        try:
            now = datetime.now(timezone.utc)
            # Simulate a few high-impact events for testing/demo
            mock_events = [
                MacroEvent(
                    name="CPI Data Release",
                    symbol="USD",
                    impact=EventImpact.HIGH,
                    timestamp=now + timedelta(hours=2),
                    pre_window_mins=self.cfg.macro_event_high_pre if self.cfg else 30,
                    post_window_mins=self.cfg.macro_event_high_post if self.cfg else 60,
                ),
                MacroEvent(
                    name="Non-Farm Payrolls (NFP)",
                    symbol="USD",
                    impact=EventImpact.HIGH,
                    timestamp=now + timedelta(days=1),
                    pre_window_mins=self.cfg.macro_event_high_pre if self.cfg else 30,
                    post_window_mins=self.cfg.macro_event_high_post if self.cfg else 60,
                ),
                MacroEvent(
                    name="FOMC Meeting Minutes",
                    symbol="USD",
                    impact=EventImpact.HIGH,
                    timestamp=now - timedelta(minutes=15),  # Currently active
                    pre_window_mins=30,
                    post_window_mins=60,
                ),
                MacroEvent(
                    name="Consumer Confidence",
                    symbol="USD",
                    impact=EventImpact.MEDIUM,
                    timestamp=now + timedelta(minutes=45),
                    pre_window_mins=15,
                    post_window_mins=30,
                ),
                MacroEvent(
                    name="Gold Demand Trends Report",
                    symbol="XAUUSD",
                    impact=EventImpact.MEDIUM,
                    timestamp=now + timedelta(hours=5),
                    pre_window_mins=15,
                    post_window_mins=30,
                ),
            ]
            self.events = mock_events
            self._last_fetch = now
            logger.debug("Fetched %d macro events (MOCK)", len(self.events))
            return self.events
        except Exception as e:
            logger.error("Failed to fetch macro events: %s", e)
            # Enterprise-safe fallback: empty list
            return []

    def get_active_events(self, current_time: Optional[datetime] = None) -> List[MacroEvent]:
        """Return events whose windows cover the current time."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Refresh events if none or stale (e.g., > 1 hour old)
        if not self.events or (self._last_fetch and (current_time - self._last_fetch) > timedelta(hours=1)):
            self.fetch_events()

        return [e for e in self.events if e.is_active(current_time)]

    def should_block_execution(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """
        Check if execution should be blocked due to HIGH impact macro risk.
        Blocks if there is a HIGH impact event for the symbol or USD.
        """
        if self.cfg and not getattr(self.cfg, "enable_macro_filter", True):
            return False

        active_events = self.get_active_events(current_time)
        high_impact_active = [
            e for e in active_events
            if e.impact == EventImpact.HIGH and (e.symbol == symbol or e.symbol == "USD" or e.symbol == "ALL")
        ]

        if high_impact_active:
            for e in high_impact_active:
                logger.warning("Execution BLOCKED | Active HIGH impact event: %s (%s)", e.name, e.symbol)
            return True

        return False

    def get_risk_multiplier(self, symbol: str, current_time: Optional[datetime] = None) -> float:
        """
        Calculate a risk multiplier based on active MEDIUM impact events.
        Reduces position size if MEDIUM impact windows are active.
        """
        if self.cfg and not getattr(self.cfg, "enable_macro_filter", True):
            return 1.0

        active_events = self.get_active_events(current_time)
        medium_impact_active = [
            e for e in active_events
            if e.impact == EventImpact.MEDIUM and (e.symbol == symbol or e.symbol == "USD" or e.symbol == "ALL")
        ]

        if medium_impact_active:
            logger.info("Risk REDUCED (0.5x) | Active MEDIUM impact events present")
            return 0.5

        return 1.0

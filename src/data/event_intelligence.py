"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Macroeconomic event ingestion and risk intelligence.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ImpactLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EconomicEvent(BaseModel):
    """Represents a macroeconomic event or risk window."""
    name: str
    symbol: str  # e.g., "USD"
    timestamp: datetime  # Start of event
    impact: ImpactLevel
    end_timestamp: Optional[datetime] = None  # End of event (for windows)
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    description: Optional[str] = None

    @property
    def is_high_impact(self) -> bool:
        return self.impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL)


class EventIntelligence:
    """
    Analyzes macroeconomic events to provide trading recommendations.
    """

    def __init__(self):
        # Default risk windows in minutes (pre-event, post-event)
        self.risk_configs = {
            ImpactLevel.CRITICAL: (60, 120),
            ImpactLevel.HIGH: (30, 60),
            ImpactLevel.MEDIUM: (15, 30),
            ImpactLevel.LOW: (0, 0),
        }

    def get_severity_score(self, event: EconomicEvent) -> int:
        """Returns a severity score from 1-10."""
        scores = {
            ImpactLevel.CRITICAL: 10,
            ImpactLevel.HIGH: 8,
            ImpactLevel.MEDIUM: 5,
            ImpactLevel.LOW: 2,
        }
        return scores.get(event.impact, 1)

    def is_in_risk_window(self, event: EconomicEvent, current_time: datetime) -> bool:
        """Checks if the current time is within the risk window of an event."""
        # Ensure current_time is timezone-aware
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        pre, post = self.risk_configs.get(event.impact, (0, 0))

        start_window = event.timestamp - timedelta(minutes=pre)

        # If the event has an end_timestamp, it's a duration-based risk window
        effective_end = event.end_timestamp or event.timestamp
        end_window = effective_end + timedelta(minutes=post)

        return start_window <= current_time <= end_window

    def get_trading_recommendation(
        self, events: List[EconomicEvent], current_time: datetime
    ) -> Dict[str, Any]:
        """
        Analyzes a list of events and provides a consolidated trading recommendation.
        """
        active_risk_events = [
            e for e in events if self.is_in_risk_window(e, current_time)
        ]

        if not active_risk_events:
            return {
                "block_execution": False,
                "position_size_multiplier": 1.0,
                "reason": "No high-impact events active.",
            }

        # Find the most severe active event
        max_severity_event = max(active_risk_events, key=self.get_severity_score)
        impact = max_severity_event.impact

        if impact == ImpactLevel.CRITICAL:
            return {
                "block_execution": True,
                "position_size_multiplier": 0.0,
                "reason": f"CRITICAL event active: {max_severity_event.name}",
            }
        elif impact == ImpactLevel.HIGH:
            return {
                "block_execution": False,
                "position_size_multiplier": 0.5,
                "reason": f"HIGH impact event active: {max_severity_event.name}",
            }
        elif impact == ImpactLevel.MEDIUM:
            return {
                "block_execution": False,
                "position_size_multiplier": 0.75,
                "reason": f"MEDIUM impact event active: {max_severity_event.name}",
            }

        return {
            "block_execution": False,
            "position_size_multiplier": 1.0,
            "reason": "Low impact events active, no restrictions.",
        }


@runtime_checkable
class EventProvider(Protocol):
    """Interface for external event data providers."""

    def fetch_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Fetches events within a given timeframe."""
        ...


class MockEventProvider:
    """Mock provider for testing and fallback."""

    def __init__(self, mock_events: Optional[List[EconomicEvent]] = None):
        self.mock_events = mock_events or []

    def fetch_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        return [
            e for e in self.mock_events
            if start_date <= e.timestamp <= end_date
        ]


class EventManager:
    """
    Manages event ingestion and intelligence.
    """

    def __init__(self, provider: EventProvider):
        self.provider = provider
        self.intelligence = EventIntelligence()
        self._cached_events: List[EconomicEvent] = []

    def refresh_events(self, days_ahead: int = 7):
        """Refreshes the internal event cache."""
        try:
            start = datetime.now(timezone.utc) - timedelta(days=1)
            end = datetime.now(timezone.utc) + timedelta(days=days_ahead)
            self._cached_events = self.provider.fetch_events(start, end)
        except Exception as e:
            logger.error("error_fetching_events", error=str(e))

    def get_current_recommendation(self) -> Dict[str, Any]:
        """Gets recommendation based on current time."""
        return self.intelligence.get_trading_recommendation(
            self._cached_events, datetime.now(timezone.utc)
        )

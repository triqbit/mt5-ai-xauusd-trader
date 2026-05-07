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
from datetime import UTC, datetime, timedelta

from src.core.constants import EventCategory, EventImpact
from src.data.event_models import MacroEvent, RiskStatus

logger = logging.getLogger(__name__)

__all__ = [
    "EventImpact",
    "EventCategory",
    "MacroEvent",
    "RiskStatus",
    "BaseEventProvider",
    "MockEventProvider",
    "JSONEventProvider",
    "MetaAPIEventProvider",
    "TradingViewEventProvider",
    "EventIntelligence",
]


class BaseEventProvider(ABC):
    """Abstract base class for event data providers."""

    @abstractmethod
    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        """Fetch events within a time range."""
        pass


class MockEventProvider(BaseEventProvider):
    """Mock provider for testing and fallback."""

    def __init__(self, mock_events: list[MacroEvent] | None = None):
        self.events = mock_events or []

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        return [
            e
            for e in self.events
            if (e.end_timestamp or e.timestamp) >= start_time and e.timestamp <= end_time
        ]


class JSONEventProvider(BaseEventProvider):
    """Provider that reads events from a local JSON file."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        import json
        import os

        if not os.path.exists(self.file_path):
            logger.warning(f"Event file {self.file_path} not found.")
            return []

        try:
            with open(self.file_path) as f:
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


class TradingViewEventProvider(BaseEventProvider):
    """
    Mocked provider for TradingView economic calendar.
    In a real implementation, this would use scraping or an unofficial API.
    """

    def __init__(self):
        self._impact_map = {
            "low": EventImpact.LOW,
            "medium": EventImpact.MEDIUM,
            "high": EventImpact.HIGH,
        }

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        # Implementation left as mock for now, demonstrating multi-source capability.
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
            "critical": EventImpact.CRITICAL,
        }

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
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

                # Filter for XAUUSD relevant events:
                # 1. US/USD events
                # 2. Geopolitical events (regardless of country)
                # 3. High/Critical impact events from other major economies
                is_usd = item.get("country") == "US" or item.get("currency") == "USD"
                is_geopolitical = category == EventCategory.GEOPOLITICAL
                is_major_economy = item.get("country") in ["EU", "GB", "JP", "CH", "CN"]
                impact_str = item.get("impact", "low").lower()
                impact = self._impact_map.get(impact_str, EventImpact.LOW)

                if not (is_usd or is_geopolitical or (is_major_economy and impact >= EventImpact.HIGH)):
                    continue

                # MetaAPI uses UTC ISO strings
                ts = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))

                macro_events.append(
                    MacroEvent(
                        name=name,
                        category=category,
                        impact=impact,
                        timestamp=ts,
                    )
                )
            return macro_events

        except Exception as e:
            logger.error(f"MetaAPI event fetch failed: {e}")
            return []

    def _guess_category(self, name: str) -> EventCategory:
        """Guesses the event category based on the event name."""
        name_upper = name.upper()
        if any(kw in name_upper for kw in ["CPI", "INFLATION", "PCE", "CONSUMER PRICE"]):
            return EventCategory.CPI
        if any(
            kw in name_upper
            for kw in ["NON-FARM PAYROLL", "NFP", "UNEMPLOYMENT", "EMPLOYMENT", "JOBLESS"]
        ):
            return EventCategory.NFP
        if any(kw in name_upper for kw in ["FOMC", "FED ", "FEDERAL RESERVE", "POWELL", "DOT PLOT"]):
            return EventCategory.FOMC
        if (
            any(kw in name_upper for kw in ["RATE", "INTEREST", "DECISION", "BENCHMARK"])
            and any(
                kw in name_upper
                for kw in ["DECISION", "STATEMENT", "MINUTES", "PRESS CONFERENCE", "TARGET"]
            )
        ) or "FUNDS RATE" in name_upper:
            return EventCategory.RATES
        if any(
            kw in name_upper
            for kw in [
                "WAR",
                "CONFLICT",
                "SANCTION",
                "GEOPOLITICAL",
                "ELECTION",
                "TENSION",
                "ESCALATION",
                "MISSILE",
                "STRIKE",
                "SAFE HAVEN",
            ]
        ):
            return EventCategory.GEOPOLITICAL
        if any(
            kw in name_upper
            for kw in [
                "GDP",
                "PMI",
                "ISM",
                "RETAIL SALES",
                "CONSUMER CONFIDENCE",
                "TREASURY",
                "YIELD",
                "BOND AUCTION",
                "DURABLE GOODS",
                "HOUSING STARTS",
                "MANUFACTURING",
                "CENTRAL BANK",
            ]
        ):
            return EventCategory.USD_MACRO
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
        providers: list[BaseEventProvider],
        pre_event_minutes: dict[EventImpact, int] | None = None,
        post_event_minutes: dict[EventImpact, int] | None = None,
    ):
        self.providers = providers
        self._cached_events: list[MacroEvent] = []
        self._last_successful_fetch: datetime | None = None
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

    def refresh(self, current_time: datetime | None = None) -> None:
        """
        Force a refresh of event data from all providers.
        """
        now = current_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())
        start_lookback = now - timedelta(minutes=max_post + 1440)
        end_lookahead = now + timedelta(minutes=max_pre + 1440)

        events: list[MacroEvent] = []
        any_success = False
        for provider in self.providers:
            try:
                provider_events = provider.get_upcoming_events(start_lookback, end_lookahead)
                events.extend(provider_events)
                any_success = True
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed during refresh: {e}")

        if any_success:
            unique_events = {}
            for e in events:
                key = (e.name, e.timestamp)
                if key not in unique_events:
                    unique_events[key] = e
            self._cached_events = list(unique_events.values())
            self._last_successful_fetch = now

    def get_risk_status(self, current_time: datetime | None = None) -> RiskStatus:
        """
        Calculates the current risk status based on upcoming and recent events.
        """
        now = current_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        # Look ahead and behind based on max windows
        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())

        # Also consider major event minimum windows (120m pre, 180m post)
        max_pre = max(max_pre, 120)
        max_post = max(max_post, 180)

        # Extend windows for long-duration events
        start_lookback = now - timedelta(minutes=max_post + 1440)  # +1 day for long events
        end_lookahead = now + timedelta(minutes=max_pre + 1440)

        events: list[MacroEvent] = []
        all_fetch_failed = True

        for provider in self.providers:
            try:
                provider_events = provider.get_upcoming_events(start_lookback, end_lookahead)
                if provider_events is not None:
                    events.extend(provider_events)
                    all_fetch_failed = False
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed to fetch events: {e}")

        # De-duplicate events by name and timestamp
        if not all_fetch_failed:
            unique_events = {}
            for e in events:
                key = (e.name, e.timestamp)
                if key not in unique_events:
                    unique_events[key] = e
            events = list(unique_events.values())

            # Update cache on success (if we got at least some events)
            self._cached_events = events
            self._last_successful_fetch = now
        else:
            logger.warning("All providers failed. Falling back to cached data.")
            # Use cached events, filtering for the current relevant window
            events = [
                e
                for e in self._cached_events
                if (e.end_timestamp or e.timestamp) >= start_lookback and e.timestamp <= end_lookahead
            ]

        if not events and all_fetch_failed:
            # If no cached data is available, return safe-mode status.
            return RiskStatus(
                is_blocked=False, risk_multiplier=1.0, reason="Event data unavailable (no cache)"
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
                event_mult = 1.0
                if event.impact == EventImpact.CRITICAL:
                    event_mult = 0.0
                elif event.impact == EventImpact.HIGH:
                    event_mult = 0.5
                elif event.impact == EventImpact.MEDIUM:
                    event_mult = 0.75

                # Stricter multiplier for major events
                if event.category in [EventCategory.FOMC, EventCategory.NFP, EventCategory.RATES]:
                    if event.impact >= EventImpact.HIGH:
                        event_mult = min(event_mult, 0.0 if event.impact == EventImpact.CRITICAL else 0.25)

                min_multiplier = min(min_multiplier, event_mult)

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

    def should_block_execution(self, current_time: datetime | None = None) -> bool:
        """Helper to check if execution should be blocked."""
        return self.get_risk_status(current_time).is_blocked

    def get_risk_multiplier(self, current_time: datetime | None = None) -> float:
        """Helper to get the current risk multiplier."""
        return self.get_risk_status(current_time).risk_multiplier

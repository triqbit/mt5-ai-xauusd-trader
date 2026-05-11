"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/data/event_intelligence.py
Ingests and normalizes high-impact macroeconomic events relevant to XAUUSD.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

import structlog

from src.core.constants import EventCategory, EventImpact
from src.data.event_models import MacroEvent, RiskStatus

logger = structlog.get_logger(__name__)

__all__ = [
    "BaseEventProvider",
    "EventCategory",
    "EventImpact",
    "EventIntelligence",
    "JSONEventProvider",
    "MacroEvent",
    "MetaAPIEventProvider",
    "MockEventProvider",
    "RiskStatus",
    "TradingViewEventProvider",
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
    Generates realistic synthetic events for testing and integration.
    """

    def __init__(self):
        self._impact_map = {
            "low": EventImpact.LOW,
            "medium": EventImpact.MEDIUM,
            "high": EventImpact.HIGH,
        }

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        """
        Generates synthetic macro events based on deterministic patterns.
        Useful for pipeline verification without external API dependencies.
        """
        events = []
        current = start_time.replace(minute=0, second=0, microsecond=0)

        while current <= end_time:
            # 1. NFP: First Friday of the month at 13:30 UTC
            if current.weekday() == 4 and 1 <= current.day <= 7:
                nfp_time = current.replace(hour=13, minute=30)
                if start_time <= nfp_time <= end_time:
                    events.append(
                        MacroEvent(
                            name="Non-Farm Payrolls (TV Mock)",
                            category=EventCategory.NFP,
                            impact=EventImpact.HIGH,
                            timestamp=nfp_time,
                        )
                    )

            # 2. CPI: Second Wednesday of the month at 12:30 UTC
            if current.weekday() == 2 and 8 <= current.day <= 14:
                cpi_time = current.replace(hour=12, minute=30)
                if start_time <= cpi_time <= end_time:
                    events.append(
                        MacroEvent(
                            name="CPI m/m (TV Mock)",
                            category=EventCategory.CPI,
                            impact=EventImpact.HIGH,
                            timestamp=cpi_time,
                        )
                    )

            # 3. Geopolitical: Random-ish but deterministic based on day
            if current.day % 10 == 0 and current.hour == 9:
                geo_time = current.replace(minute=0)
                if start_time <= geo_time <= end_time:
                    events.append(
                        MacroEvent(
                            name="Geopolitical Tension Alert (TV Mock)",
                            category=EventCategory.GEOPOLITICAL,
                            impact=EventImpact.MEDIUM,
                            timestamp=geo_time,
                        )
                    )

            current += timedelta(hours=24)

        return events


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
        self._session = self._init_session()

    def _init_session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        return session

    def get_upcoming_events(self, start_time: datetime, end_time: datetime) -> list[MacroEvent]:
        """
        Fetches events via MetaAPI's REST interface with retries and structured logging.
        """
        url = "https://calendar.metaapi.cloud/events"
        params = {
            "startTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        headers = {"auth-token": self.token}

        try:
            logger.info(
                "Fetching MetaAPI events",
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )
            # We use the persistent session for connection pooling and retries.
            response = self._session.get(url, params=params, headers=headers, timeout=15)
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

                if not (
                    is_usd or is_geopolitical or (is_major_economy and impact >= EventImpact.HIGH)
                ):
                    continue

                # MetaAPI uses UTC ISO strings
                ts = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))

                macro_events.append(
                    MacroEvent(
                        name=name,
                        category=category,
                        impact=impact,
                        timestamp=ts,
                        actual=item.get("actual"),
                        forecast=item.get("forecast"),
                        previous=item.get("previous"),
                    )
                )
            return macro_events

        except Exception as e:
            logger.error(
                "MetaAPI event fetch failed",
                error=str(e),
                url=url,
                start_time=start_time.isoformat(),
            )
            return []

    def _guess_category(self, name: str) -> EventCategory:
        """Guesses the event category based on the event name."""
        name_upper = name.upper()
        if any(kw in name_upper for kw in ["CPI", "INFLATION", "PCE", "CONSUMER PRICE", "PPI"]):
            return EventCategory.CPI
        if any(
            kw in name_upper
            for kw in [
                "NON-FARM PAYROLL",
                "NFP",
                "UNEMPLOYMENT",
                "EMPLOYMENT",
                "JOBLESS",
                "JOBLESS CLAIMS",
            ]
        ):
            return EventCategory.NFP
        if any(
            kw in name_upper for kw in ["FOMC", "FED ", "FEDERAL RESERVE", "POWELL", "DOT PLOT"]
        ) and "PHILLY FED" not in name_upper:
            return EventCategory.FOMC
        if (
            any(kw in name_upper for kw in ["RATE", "INTEREST", "DECISION", "BENCHMARK"])
            and any(
                kw in name_upper
                for kw in ["DECISION", "STATEMENT", "MINUTES", "PRESS CONFERENCE", "TARGET"]
            )
        ) or any(kw in name_upper for kw in ["FUNDS RATE", "MONETARY POLICY"]):
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
                "TERROR",
                "ATTACK",
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
                "TRADE BALANCE",
                "FACTORY ORDERS",
                "EMPIRE STATE",
                "PHILLY FED",
                "OPEC",
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
        refresh_interval_minutes: int = 5,
        fail_safe_blocked: bool = False,
        config: Any | None = None,
    ):
        self.providers = providers
        self._cached_events: list[MacroEvent] = []
        self._last_successful_fetch: datetime | None = None
        self.refresh_interval = timedelta(minutes=refresh_interval_minutes)
        self.fail_safe_blocked = fail_safe_blocked
        self.config = config

        # Default risk windows (minutes)
        if config and hasattr(config, "macro_pre_event_minutes"):
            # Map dict[int, int] to dict[EventImpact, int]
            self.pre_event_minutes = {
                EventImpact(k): v for k, v in config.macro_pre_event_minutes.items()
            }
        else:
            self.pre_event_minutes = pre_event_minutes or {
                EventImpact.LOW: 5,
                EventImpact.MEDIUM: 15,
                EventImpact.HIGH: 60,
                EventImpact.CRITICAL: 120,
            }

        if config and hasattr(config, "macro_post_event_minutes"):
            self.post_event_minutes = {
                EventImpact(k): v for k, v in config.macro_post_event_minutes.items()
            }
        else:
            self.post_event_minutes = post_event_minutes or {
                EventImpact.LOW: 5,
                EventImpact.MEDIUM: 30,
                EventImpact.HIGH: 120,
                EventImpact.CRITICAL: 240,
            }

    def refresh(self, current_time: datetime | None = None) -> None:
        """
        Force a refresh of event data from all providers.
        Merges newly fetched events into the cache instead of overwriting.
        """
        now = current_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())

        # Major event minimum windows
        max_pre = max(max_pre, 120)
        max_post = max(max_post, 180)

        start_lookback = now - timedelta(minutes=max_post + 1440)
        end_lookahead = now + timedelta(minutes=max_pre + 1440)

        new_events: list[MacroEvent] = []
        any_success = False
        for provider in self.providers:
            try:
                provider_events = provider.get_upcoming_events(start_lookback, end_lookahead)
                if provider_events is not None:
                    new_events.extend(provider_events)
                    any_success = True
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed during refresh: {e}")

        if any_success:
            # Use a dictionary for merging to preserve uniqueness and prevent data loss
            # from temporarily failing providers.
            unique_events = {(e.name, e.timestamp): e for e in self._cached_events}
            for e in new_events:
                unique_events[(e.name, e.timestamp)] = e

            # Filter out stale events from cache to keep it performant
            stale_threshold = now - timedelta(days=2)
            self._cached_events = [
                e for e in unique_events.values()
                if (e.end_timestamp or e.timestamp) >= stale_threshold
            ]
            self._last_successful_fetch = now

    def get_risk_status(self, current_time: datetime | None = None) -> RiskStatus:
        """
        Calculates the current risk status based on upcoming and recent events.
        Uses cached data if it's within the refresh_interval.
        """
        now = current_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        # Determine if we need to refresh cache
        needs_refresh = (
            self._last_successful_fetch is None
            or (now - self._last_successful_fetch) > self.refresh_interval
            or not self._cached_events
        )

        if needs_refresh:
            self.refresh(now)

        # Re-verify if fetch failed completely and we have no cache
        all_fetch_failed = self._last_successful_fetch is None or (
            needs_refresh and (now - self._last_successful_fetch) > timedelta(seconds=1)
        )

        # Look ahead and behind based on max windows
        max_pre = max(self.pre_event_minutes.values())
        max_post = max(self.post_event_minutes.values())
        max_pre = max(max_pre, 120)
        max_post = max(max_post, 180)

        start_lookback = now - timedelta(minutes=max_post + 1440)
        end_lookahead = now + timedelta(minutes=max_pre + 1440)

        # Always filter the cache for the current relevant window
        events = [
            e
            for e in self._cached_events
            if (e.end_timestamp or e.timestamp) >= start_lookback and e.timestamp <= end_lookahead
        ]

        if not events and (all_fetch_failed or self._last_successful_fetch is None):
            # If no data is available and providers failed (or haven't succeeded yet),
            # return status based on fail_safe_blocked setting.
            reason = "Event data unavailable (no cache)"
            return RiskStatus(
                is_blocked=self.fail_safe_blocked,
                risk_multiplier=0.0 if self.fail_safe_blocked else 1.0,
                reason=reason,
            )

        active_events = []
        blocking_events = []
        is_blocked = False
        min_multiplier = 1.0

        for event in events:
            pre_window = self.pre_event_minutes.get(event.impact, 0)
            post_window = self.post_event_minutes.get(event.impact, 0)

            # Adjust windows based on category
            if event.category in [
                EventCategory.FOMC,
                EventCategory.NFP,
                EventCategory.RATES,
                EventCategory.CPI,
            ]:
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
                            EventCategory.CPI,
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
                        EventCategory.CPI,
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
                if (
                    event.category
                    in [
                        EventCategory.FOMC,
                        EventCategory.NFP,
                        EventCategory.RATES,
                        EventCategory.CPI,
                    ]
                    and event.impact >= EventImpact.HIGH
                ):
                    event_mult = min(
                        event_mult, 0.0 if event.impact == EventImpact.CRITICAL else 0.25
                    )

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

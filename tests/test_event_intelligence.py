"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_event_intelligence.py
Unified test suite for EventIntelligence and EventProviders.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.data.event_intelligence import (
    BaseEventProvider,
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MetaAPIEventProvider,
    MockEventProvider,
    TradingViewEventProvider,
)


@pytest.fixture
def now():
    return datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)


def test_event_intelligence_blocking(now):
    """Test that HIGH impact events correctly block trading."""
    event = MacroEvent(
        name="FOMC Interest Rate Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=30),
    )
    provider = MagicMock()
    provider.get_upcoming_events.return_value = [event]

    intel = EventIntelligence([provider])
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert "FOMC Interest Rate Decision" in status.reason


def test_event_intelligence_multiplier(now):
    """Test that MEDIUM impact events reduce risk but don't block."""
    event = MacroEvent(
        name="USD Consumer Confidence",
        category=EventCategory.USD,
        impact=EventImpact.MEDIUM,
        timestamp=now + timedelta(minutes=10),
    )
    provider = MagicMock()
    provider.get_upcoming_events.return_value = [event]

    intel = EventIntelligence([provider])
    status = intel.get_risk_status(now)

    assert status.is_blocked is False
    assert status.risk_multiplier == 0.75


def test_event_intelligence_cooldown(now):
    """Test post-event cooldown windows."""
    event = MacroEvent(
        name="Critical Event",
        category=EventCategory.USD,
        impact=EventImpact.CRITICAL,
        timestamp=now - timedelta(minutes=10),
    )
    provider = MagicMock()
    provider.get_upcoming_events.return_value = [event]

    intel = EventIntelligence([provider])
    status = intel.get_risk_status(now)

    assert status.is_blocked is True


def test_cache_deduplication(now):
    """Test that duplicate events from different providers are merged."""
    event1 = MacroEvent(
        name="Shared Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=10),
    )
    event2 = MacroEvent(
        name="Shared Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=10),
    )
    event3 = MacroEvent(
        name="Unique Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=15),
    )

    provider1 = MagicMock()
    provider1.get_upcoming_events.return_value = [event1, event3]

    provider2 = MagicMock()
    provider2.get_upcoming_events.return_value = [event2]

    intel = EventIntelligence([provider1, provider2])
    intel.get_risk_status(now)

    assert len(intel._cached_events) == 2
    names = [e.name for e in intel._cached_events]
    assert names.count("Shared Event") == 1
    assert "Unique Event" in names


def test_provider_failure_resilience(now):
    """Test that EventIntelligence survives when some providers fail."""
    event = MacroEvent(
        name="Success Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=2),
    )

    provider_fail = MagicMock()
    provider_fail.get_upcoming_events.side_effect = Exception("Network Error")

    provider_ok = MagicMock()
    provider_ok.get_upcoming_events.return_value = [event]

    intel = EventIntelligence([provider_fail, provider_ok])
    status = intel.get_risk_status(now)

    assert len(status.active_events) == 1
    assert status.active_events[0].name == "Success Event"


def test_refresh_interval_logic(now):
    """Test that EventIntelligence respects the refresh_interval."""
    event = MacroEvent(
        name="Test Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now,
    )
    provider = MagicMock()
    provider.get_upcoming_events.return_value = [event]

    # 5 minute refresh interval
    intel = EventIntelligence([provider], refresh_interval_minutes=5)

    # First call - should hit provider
    intel.get_risk_status(now)
    assert provider.get_upcoming_events.call_count == 1

    # Second call (2 mins later) - should NOT hit provider
    intel.get_risk_status(now + timedelta(minutes=2))
    assert provider.get_upcoming_events.call_count == 1

    # Third call (6 mins later) - should hit provider
    intel.get_risk_status(now + timedelta(minutes=6))
    assert provider.get_upcoming_events.call_count == 2


def test_fail_safe_blocked_true(now):
    """Test that fail_safe_blocked=True blocks when no data is available."""

    class FailingProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([FailingProvider()], fail_safe_blocked=True)
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert "Event data unavailable (no cache)" in status.reason


def test_fail_safe_blocked_false(now):
    """Test that fail_safe_blocked=False does not block when no data is available."""

    class FailingProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([FailingProvider()], fail_safe_blocked=False)
    status = intel.get_risk_status(now)

    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0


def test_tradingview_mock_provider(now):
    """Test the TradingView mock provider returns events for known dates."""
    provider = TradingViewEventProvider()

    # Check NFP (First Friday of May 2024 is May 3)
    start = datetime(2024, 5, 3, 0, 0, tzinfo=UTC)
    end = datetime(2024, 5, 3, 23, 59, tzinfo=UTC)
    events = provider.get_upcoming_events(start, end)
    assert any("Non-Farm Payrolls" in e.name for e in events)

    # Check CPI (Second Wednesday of May 2024 is May 8)
    start = datetime(2024, 5, 8, 0, 0, tzinfo=UTC)
    end = datetime(2024, 5, 8, 23, 59, tzinfo=UTC)
    events = provider.get_upcoming_events(start, end)
    assert any("CPI" in e.name for e in events)


def test_event_durations(now):
    """Test category-based default durations."""
    geo_event = MacroEvent(
        name="War breakout",
        category=EventCategory.GEOPOLITICAL,
        impact=EventImpact.HIGH,
        timestamp=now,
    )
    assert geo_event.end_timestamp == now + timedelta(hours=24)

    cb_event = MacroEvent(
        name="Fed Rate Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.CRITICAL,
        timestamp=now,
    )
    assert cb_event.end_timestamp == now + timedelta(hours=4)


@patch("src.data.event_intelligence.MetaAPIEventProvider._init_session")
def test_metaapi_provider_extra_fields(mock_init_session, now):
    mock_session = MagicMock()
    mock_init_session.return_value = mock_session
    mock_get = mock_session.get

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "event": "Core CPI m/m",
            "impact": "high",
            "time": "2023-01-01T12:30:00.000Z",
            "currency": "USD",
            "country": "US",
            "actual": 0.3,
            "forecast": 0.2,
            "previous": 0.1,
        }
    ]
    mock_get.return_value = mock_response

    provider = MetaAPIEventProvider(token="fake_token")
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].actual == 0.3
    assert events[0].forecast == 0.2
    assert events[0].previous == 0.1


def test_event_intelligence_cache_merging(now):
    """Test that EventIntelligence merges events instead of overwriting."""
    event1 = MacroEvent(
        name="Event 1",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=5),
    )
    event2 = MacroEvent(
        name="Event 2",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=10),
    )

    class MockProvider(BaseEventProvider):
        def __init__(self, events):
            self.events = events

        def get_upcoming_events(self, start, end):
            return self.events

    provider1 = MockProvider([event1])
    intel = EventIntelligence([provider1])

    # First refresh
    intel.refresh(now)
    assert len(intel._cached_events) == 1

    # Swap provider events and refresh again
    provider1.events = [event2]
    intel.refresh(now + timedelta(seconds=1))

    # Should have both events now due to merging
    assert len(intel._cached_events) == 2
    names = [e.name for e in intel._cached_events]
    assert "Event 1" in names
    assert "Event 2" in names


def test_guess_category_enhanced_keywords():
    provider = MetaAPIEventProvider(token="fake")
    assert provider._guess_category("Core PPI m/m") == EventCategory.CPI
    assert provider._guess_category("Initial Jobless Claims") == EventCategory.NFP
    assert provider._guess_category("Monetary Policy Statement") == EventCategory.RATES
    assert provider._guess_category("Trade Balance") == EventCategory.USD_MACRO

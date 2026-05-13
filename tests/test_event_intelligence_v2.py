from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.data.event_intelligence import (
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MockEventProvider,
    TradingViewEventProvider,
)


@pytest.fixture
def now():
    return datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)

def test_refresh_interval_logic(now):
    """Test that EventIntelligence respects the refresh_interval."""
    event = MacroEvent(
        name="Test Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now
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
    """Test that fail_safe_blocked=False (default) does not block when no data is available."""
    class FailingProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([FailingProvider()], fail_safe_blocked=False)
    status = intel.get_risk_status(now)

    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0

def test_tradingview_mock_provider(now):
    """Test the TradingView mock provider returns events for known dates."""
    # May 1, 2024 is a Wednesday.
    # May 3, 2024 is the first Friday (NFP).
    # May 8, 2024 is the second Wednesday (CPI).

    provider = TradingViewEventProvider()

    # Check NFP
    start = datetime(2024, 5, 3, 0, 0, tzinfo=UTC)
    end = datetime(2024, 5, 3, 23, 59, tzinfo=UTC)
    events = provider.get_upcoming_events(start, end)
    assert any("Non-Farm Payrolls" in e.name for e in events)

    # Check CPI
    start = datetime(2024, 5, 8, 0, 0, tzinfo=UTC)
    end = datetime(2024, 5, 8, 23, 59, tzinfo=UTC)
    events = provider.get_upcoming_events(start, end)
    assert any("CPI" in e.name for e in events)

def test_geopolitical_default_duration(now):
    """Test that GEOPOLITICAL events get a 24h default duration."""
    event = MacroEvent(
        name="War breakout",
        category=EventCategory.GEOPOLITICAL,
        impact=EventImpact.HIGH,
        timestamp=now
    )
    # validate_timestamps is called on init
    assert event.end_timestamp == now + timedelta(hours=24)

def test_central_bank_default_duration(now):
    """Test that FOMC/RATES events get a 4h default duration."""
    event = MacroEvent(
        name="Fed Rate Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.CRITICAL,
        timestamp=now
    )
    assert event.end_timestamp == now + timedelta(hours=4)

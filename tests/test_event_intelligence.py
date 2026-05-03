from datetime import datetime, timedelta, timezone

import pytest

from src.data.event_intelligence import (
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MockEventProvider,
)


@pytest.fixture
def mock_events():
    now = datetime.now(timezone.utc)
    return [
        MacroEvent(
            name="CPI Data",
            category=EventCategory.CPI,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=15),
        ),
        MacroEvent(
            name="FOMC Meeting",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=now + timedelta(hours=1),
        ),
        MacroEvent(
            name="Past NFP",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(minutes=10),
        ),
        MacroEvent(
            name="Minor Event",
            category=EventCategory.OTHER,
            impact=EventImpact.LOW,
            timestamp=now + timedelta(minutes=2),
        ),
    ]


def test_risk_status_blocking():
    now = datetime.now(timezone.utc)
    events = [
        MacroEvent(
            name="CPI Data",
            category=EventCategory.CPI,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=15),
        ),
        MacroEvent(
            name="Minor Event",
            category=EventCategory.OTHER,
            impact=EventImpact.LOW,
            timestamp=now + timedelta(minutes=2),
        ),
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)

    # CPI Data is HIGH impact and in 15 mins (<= 30 mins window for blocking)
    # Minor Event is LOW impact and in 2 mins (<= 5 mins window)
    assert status.is_blocked is True
    assert "CPI Data" in status.reason
    assert status.risk_multiplier == 0.5  # HIGH impact multiplier


def test_risk_status_critical_blocking(mock_events):
    # Move current time closer to FOMC
    now = datetime.now(timezone.utc)
    fomc_time = now + timedelta(minutes=30)

    # Update FOMC event in provider
    events = [
        MacroEvent(
            name="FOMC Meeting",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=fomc_time,
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    # Check 10 mins before FOMC
    status = intel.get_risk_status(fomc_time - timedelta(minutes=10))
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0


def test_risk_status_cooldown(mock_events):
    now = datetime.now(timezone.utc)
    # Past NFP was 10 mins ago, HIGH impact has 120 mins cooldown
    events = [
        MacroEvent(
            name="Past NFP",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(minutes=10),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.risk_multiplier == 0.5
    assert len(status.active_events) == 1
    assert status.active_events[0].name == "Past NFP"


def test_no_active_events():
    now = datetime.now(timezone.utc)
    provider = MockEventProvider([])
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0
    assert len(status.active_events) == 0


def test_fallback_behavior():
    class BrokenProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence(BrokenProvider())
    status = intel.get_risk_status(datetime.now(timezone.utc))

    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0
    assert "Event data unavailable" in status.reason

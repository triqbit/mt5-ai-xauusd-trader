import pytest
import json
import os
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock
from src.data.event_intelligence import (
    EventIntelligence,
    MockEventProvider,
    JSONEventProvider,
    MetaAPIEventProvider,
    MacroEvent,
    EventCategory,
    EventImpact
)

@pytest.fixture
def now():
    return datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

@pytest.fixture
def mock_events(now):
    return [
        MacroEvent(
            name="CPI Data",
            category=EventCategory.CPI,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=15)
        ),
        MacroEvent(
            name="FOMC Meeting",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=now + timedelta(hours=1)
        ),
        MacroEvent(
            name="Past NFP",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(minutes=10)
        ),
        MacroEvent(
            name="Minor Event",
            category=EventCategory.OTHER,
            impact=EventImpact.LOW,
            timestamp=now + timedelta(minutes=2)
        )
    ]

def test_risk_status_blocking(now):
    events = [
        MacroEvent(
            name="CPI Data",
            category=EventCategory.CPI,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=15)
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert "CPI Data" in status.reason
    assert status.risk_multiplier == 0.5

def test_risk_status_critical_blocking(now):
    events = [
        MacroEvent(
            name="FOMC Meeting",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=now + timedelta(minutes=30)
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0

def test_risk_status_cooldown(now):
    # Past NFP was 10 mins ago, HIGH impact major event has 180 mins cooldown
    # and it blocks for the first 60 mins.
    events = [
        MacroEvent(
            name="Past NFP",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(minutes=10)
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.5
    assert len(status.active_events) == 1
    assert status.active_events[0].name == "Past NFP"

def test_no_active_events(now):
    provider = MockEventProvider([])
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0
    assert len(status.active_events) == 0

def test_fallback_behavior_no_cache(now):
    class BrokenProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence(BrokenProvider())
    status = intel.get_risk_status(now)

    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0
    assert "Event data unavailable (no cache)" in status.reason

def test_fallback_behavior_with_cache(now):
    class SometimesBrokenProvider(MockEventProvider):
        def __init__(self, events):
            super().__init__(events)
            self.should_fail = False

        def get_upcoming_events(self, start, end):
            if self.should_fail:
                raise Exception("API Down")
            return super().get_upcoming_events(start, end)

    event = MacroEvent(
        name="Cached Event",
        category=EventCategory.CPI,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=15)
    )
    provider = SometimesBrokenProvider([event])
    intel = EventIntelligence(provider)

    # First fetch to populate cache
    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert len(intel._cached_events) == 1

    # Second fetch with failure
    provider.should_fail = True
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert "Cached Event" in status.reason
    assert status.risk_multiplier == 0.5

def test_ongoing_event(now):
    events = [
        MacroEvent(
            name="Geopolitical Crisis",
            category=EventCategory.GEOPOLITICAL,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(hours=1),
            end_timestamp=now + timedelta(hours=1)
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.5
    assert any(e.name == "Geopolitical Crisis" for e in status.active_events)

def test_json_provider(tmp_path, now):
    event_data = [
        {
            "name": "JSON Event",
            "category": "USD",
            "impact": 3,
            "timestamp": (now + timedelta(minutes=10)).isoformat()
        }
    ]
    file_path = tmp_path / "events.json"
    file_path.write_text(json.dumps(event_data))

    provider = JSONEventProvider(str(file_path))
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].name == "JSON Event"
    assert events[0].impact == EventImpact.HIGH

@patch("requests.get")
def test_metaapi_provider(mock_get, now):
    mock_response = MagicMock()
    mock_response.status_code = 200
    # MetaAPI typically returns strings like "2023-01-01T12:30:00.000Z"
    event_time = now + timedelta(minutes=30)
    time_str = event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    mock_response.json.return_value = [
        {
            "event": "Core CPI m/m",
            "impact": "high",
            "time": time_str
        }
    ]
    mock_get.return_value = mock_response

    provider = MetaAPIEventProvider(token="fake_token")
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].name == "Core CPI m/m"
    assert events[0].category == EventCategory.CPI
    assert events[0].impact == EventImpact.HIGH

def test_major_event_extended_window(now):
    # NFP in 90 minutes. Normal HIGH impact pre-window is 60m.
    # Major events like NFP should have 120m pre-window.
    events = [
        MacroEvent(
            name="NFP",
            category=EventCategory.NFP,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=90)
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence(provider)

    status = intel.get_risk_status(now)
    assert status.is_blocked is False # Blocks at 60m for HIGH major event
    assert len(status.active_events) == 1
    assert status.risk_multiplier == 0.5

    # Check at 50m
    status = intel.get_risk_status(now + timedelta(minutes=40))
    assert status.is_blocked is True

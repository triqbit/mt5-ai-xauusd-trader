import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.data.event_intelligence import (
    BaseEventProvider,
    EventCategory,
    EventImpact,
    EventIntelligence,
    JSONEventProvider,
    MacroEvent,
    MetaAPIEventProvider,
    MockEventProvider,
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


def test_risk_status_blocking(now):
    events = [
        MacroEvent(
            name="CPI Data",
            category=EventCategory.CPI,
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(minutes=15),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert "CPI Data" in status.reason
    # risk_multiplier must be 0.0 if is_blocked is True
    assert status.risk_multiplier == 0.0


def test_risk_status_critical_blocking(now):
    events = [
        MacroEvent(
            name="FOMC Meeting",
            category=EventCategory.FOMC,
            impact=EventImpact.CRITICAL,
            timestamp=now + timedelta(minutes=30),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence([provider])

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
            timestamp=now - timedelta(minutes=10),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    # risk_multiplier must be 0.0 if is_blocked is True
    assert status.risk_multiplier == 0.0
    assert len(status.active_events) == 1
    assert status.active_events[0].name == "Past NFP"


def test_no_active_events(now):
    provider = MockEventProvider([])
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)
    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0


def test_geopolitical_provider(now):
    from src.data.event_intelligence import GeopoliticalEventProvider

    geo_data = [
        {
            "name": "Conflict Escalation",
            "impact": 4,
            "timestamp": now.isoformat(),
            "end_timestamp": (now + timedelta(hours=48)).isoformat(),
        }
    ]
    provider = GeopoliticalEventProvider(geo_data)
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].name == "Conflict Escalation"
    assert events[0].category == EventCategory.GEOPOLITICAL
    assert events[0].impact == EventImpact.CRITICAL


def test_fallback_behavior_no_cache(now):
    class BrokenProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([BrokenProvider()])
    status = intel.get_risk_status(now)

    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0
    assert "Event data unavailable (no cache). Fail-safe PASSING." in status.reason


def test_fail_safe_blocking_behavior(now):
    class BrokenProvider(MockEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([BrokenProvider()], fail_safe_blocked=True)
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert "Event data unavailable (no cache). Fail-safe BLOCKING." in status.reason


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
        timestamp=now + timedelta(minutes=15),
    )
    provider = SometimesBrokenProvider([event])
    intel = EventIntelligence([provider])

    # First fetch to populate cache
    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert len(intel._cached_events) == 1

    # Second fetch with failure
    provider.should_fail = True
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert "Cached Event" in status.reason
    assert status.risk_multiplier == 0.0


def test_ongoing_event(now):
    events = [
        MacroEvent(
            name="Geopolitical Crisis",
            category=EventCategory.GEOPOLITICAL,
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(hours=1),
            end_timestamp=now + timedelta(hours=1),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert any(e.name == "Geopolitical Crisis" for e in status.active_events)


def test_json_provider(tmp_path, now):
    event_data = [
        {
            "name": "JSON Event",
            "category": "USD",
            "impact": 3,
            "timestamp": (now + timedelta(minutes=10)).isoformat(),
        }
    ]
    file_path = tmp_path / "events.json"
    file_path.write_text(json.dumps(event_data))

    provider = JSONEventProvider(str(file_path))
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].name == "JSON Event"
    assert events[0].impact == EventImpact.HIGH


@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider(mock_get_client, now):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_get = mock_client.get

    mock_response = MagicMock()
    mock_response.status_code = 200
    # MetaAPI typically returns strings like "2023-01-01T12:30:00.000Z"
    event_time = now + timedelta(minutes=30)
    time_str = event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    mock_response.json.return_value = [
        {
            "event": "Core CPI m/m",
            "impact": "high",
            "time": time_str,
            "currency": "USD",
            "country": "US",
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
            timestamp=now + timedelta(minutes=90),
        )
    ]
    provider = MockEventProvider(events)
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)
    assert status.is_blocked is False  # Blocks at 60m for HIGH major event
    assert len(status.active_events) == 1
    # NFP is a major event, so it gets a stricter multiplier (0.25)
    assert status.risk_multiplier == 0.25

    # Check at 50m
    status = intel.get_risk_status(now + timedelta(minutes=40))
    assert status.is_blocked is True


def test_guess_category_new_keywords():
    provider = MetaAPIEventProvider(token="fake")
    assert provider._guess_category("Geopolitical Tension") == EventCategory.GEOPOLITICAL
    assert provider._guess_category("US Treasury Bond Auction") == EventCategory.USD_MACRO


@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider_filtering(mock_get_client, now):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_get = mock_client.get

    mock_response = MagicMock()
    mock_response.status_code = 200
    event_time = now + timedelta(minutes=30)
    time_str = event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    mock_response.json.return_value = [
        {
            "event": "USD Event",
            "impact": "high",
            "time": time_str,
            "currency": "USD",
            "country": "US",
        },
        {
            "event": "EUR Event",
            "impact": "high",
            "time": time_str,
            "currency": "EUR",
            "country": "EU",
        },
    ]
    mock_get.return_value = mock_response

    provider = MetaAPIEventProvider(token="fake_token")
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    # Should include both USD and EU High Impact event
    assert len(events) == 2
    names = [e.name for e in events]
    assert "USD Event" in names
    assert "EUR Event" in names


def test_macro_event_properties(now):
    event = MacroEvent(
        name="Test", category=EventCategory.OTHER, impact=EventImpact.HIGH, timestamp=now
    )
    assert event.is_high_impact is True

    event = event.model_copy(update={"end_timestamp": now + timedelta(hours=1)})
    assert event.is_ongoing(now + timedelta(minutes=30)) is True
    assert event.is_ongoing(now - timedelta(minutes=1)) is False


def test_json_provider_missing_file():
    provider = JSONEventProvider("non_existent.json")
    assert provider.get_upcoming_events(datetime.now(), datetime.now()) is None


def test_json_provider_error(tmp_path):
    file_path = tmp_path / "corrupt.json"
    file_path.write_text("invalid json")
    provider = JSONEventProvider(str(file_path))
    assert provider.get_upcoming_events(datetime.now(), datetime.now()) is None


@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider_error(mock_get_client, now):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_get = mock_client.get

    mock_get.side_effect = Exception("Network Error")
    provider = MetaAPIEventProvider(token="fake")
    assert provider.get_upcoming_events(now, now) is None


def test_guess_category_more_keywords():
    provider = MetaAPIEventProvider(token="fake")
    assert provider._guess_category("Federal Reserve Meeting") == EventCategory.FOMC
    assert provider._guess_category("Interest Rate Decision") == EventCategory.RATES
    assert provider._guess_category("GDP Annualized") == EventCategory.USD_MACRO
    assert provider._guess_category("USD Strength Index") == EventCategory.USD


def test_event_intelligence_helpers(now):
    event = MacroEvent(
        name="Blocked",
        category=EventCategory.FOMC,
        impact=EventImpact.CRITICAL,
        timestamp=now + timedelta(minutes=10),
    )
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider])

    assert intel.should_block_execution(now) is True
    assert intel.get_risk_multiplier(now) == 0.0


def test_fallback_no_events(now):
    class FailingProvider(BaseEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("Fail")

    intel = EventIntelligence([FailingProvider()])
    status = intel.get_risk_status(now)
    assert status.is_blocked is False
    assert status.risk_multiplier == 1.0

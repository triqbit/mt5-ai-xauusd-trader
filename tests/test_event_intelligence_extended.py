from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.data.event_intelligence import (
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MetaAPIEventProvider,
)


@pytest.fixture
def now():
    return datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider_comprehensive(mock_get_client, now):
    mock_session = MagicMock()
    mock_get_client.return_value = mock_session
    mock_get = mock_session.get

    """Test MetaAPI provider with various event types and countries."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_response.json.return_value = [
        {
            "event": "Core CPI m/m",
            "impact": "high",
            "time": "2023-01-01T12:30:00.000Z",
            "currency": "USD",
            "country": "US"
        },
        {
            "event": "FOMC Statement",
            "impact": "critical",
            "time": "2023-01-01T14:00:00.000Z",
            "currency": "USD",
            "country": "US"
        },
        {
            "event": "Geopolitical Tension in Middle East",
            "impact": "high",
            "time": "2023-01-01T12:00:00.000Z",
            "currency": "EUR",
            "country": "DE"
        },
        {
            "event": "German ZEW Economic Sentiment",
            "impact": "medium",
            "time": "2023-01-01T10:00:00.000Z",
            "currency": "EUR",
            "country": "DE"
        },
        {
            "event": "ECB Monetary Policy Statement",
            "impact": "high",
            "time": "2023-01-01T13:45:00.000Z",
            "currency": "EUR",
            "country": "EU"
        }
    ]
    mock_get.return_value = mock_response

    provider = MetaAPIEventProvider(token="fake_token")
    events = provider.get_upcoming_events(now - timedelta(hours=5), now + timedelta(hours=5))

    # Expected: CPI (USD), FOMC (USD), Geopolitical (Any), ECB (EU High Impact)
    # Filtered out: German ZEW (DE Medium Impact)
    assert len(events) == 4
    names = [e.name for e in events]
    assert "Core CPI m/m" in names
    assert "FOMC Statement" in names
    assert "Geopolitical Tension in Middle East" in names
    assert "ECB Monetary Policy Statement" in names
    assert "German ZEW Economic Sentiment" not in names

def test_multi_provider_deduplication(now):
    """Test that EventIntelligence correctly de-duplicates events from multiple providers."""
    event1 = MacroEvent(
        name="Shared Event",
        category=EventCategory.CPI,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=30)
    )
    event2 = MacroEvent(
        name="Shared Event",
        category=EventCategory.CPI,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=30)
    )
    event3 = MacroEvent(
        name="Unique Event",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=60)
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
        timestamp=now + timedelta(minutes=2)
    )

    provider_fail = MagicMock()
    provider_fail.get_upcoming_events.side_effect = Exception("Network Error")

    provider_ok = MagicMock()
    provider_ok.get_upcoming_events.return_value = [event]

    intel = EventIntelligence([provider_fail, provider_ok])
    status = intel.get_risk_status(now)

    assert len(status.active_events) == 1
    assert status.active_events[0].name == "Success Event"

def test_stricter_major_event_multipliers(now):
    """Test that FOMC/NFP/RATES have stricter multipliers."""
    # Generic HIGH impact
    event_generic = MacroEvent(
        name="Generic High",
        category=EventCategory.OTHER,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=5)
    )
    provider = MagicMock()
    provider.get_upcoming_events.return_value = [event_generic]
    intel_generic = EventIntelligence([provider])
    status_generic = intel_generic.get_risk_status(now)
    # risk_multiplier must be 0.0 if is_blocked is True
    assert status_generic.risk_multiplier == 0.0

    # Major HIGH impact
    event_major = MacroEvent(
        name="FOMC Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=5)
    )
    provider_major = MagicMock()
    provider_major.get_upcoming_events.return_value = [event_major]
    intel_major = EventIntelligence([provider_major])
    status_major = intel_major.get_risk_status(now)
    # risk_multiplier must be 0.0 if is_blocked is True
    assert status_major.risk_multiplier == 0.0

@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider_unsupported_impact(mock_get_client, now):
    """Test fallback for unknown impact levels in MetaAPI."""
    mock_session = MagicMock()
    mock_get_client.return_value = mock_session
    mock_get = mock_session.get

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "event": "Unknown Impact Event",
            "impact": "extreme", # Not in our map
            "time": "2023-01-01T12:30:00.000Z",
            "currency": "USD",
            "country": "US"
        }
    ]
    mock_get.return_value = mock_response

    provider = MetaAPIEventProvider(token="fake")
    events = provider.get_upcoming_events(now, now + timedelta(hours=1))
    assert len(events) == 1
    assert events[0].impact == EventImpact.LOW # Default fallback

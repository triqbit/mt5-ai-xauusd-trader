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
)


@pytest.fixture
def now():
    return datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

@patch("src.data.event_intelligence.MetaAPIEventProvider._get_client")
def test_metaapi_provider_extra_fields(mock_get_client, now):
    mock_session = MagicMock()
    mock_get_client.return_value = mock_session
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
            "previous": 0.1
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
        timestamp=now + timedelta(minutes=5)
    )
    event2 = MacroEvent(
        name="Event 2",
        category=EventCategory.USD,
        impact=EventImpact.LOW,
        timestamp=now + timedelta(minutes=10)
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
    assert intel._cached_events[0].name == "Event 1"

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
    assert provider._guess_category("Empire State Manufacturing Index") == EventCategory.USD_MACRO
    assert provider._guess_category("Philly Fed Manufacturing Index") == EventCategory.USD_MACRO
    assert provider._guess_category("Trade Balance") == EventCategory.USD_MACRO

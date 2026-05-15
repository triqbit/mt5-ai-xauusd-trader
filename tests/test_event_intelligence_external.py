import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch
from src.data.event_intelligence import MetaAPIEventProvider, EventCategory, EventImpact

@pytest.fixture
def now():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

@patch("src.data.event_intelligence.MetaAPIEventProvider._init_client")
def test_metaapi_external_feed_mock(mock_init_client, now):
    """
    Specifically verifies that MetaAPIEventProvider correctly handles
    external feed data when mocked, meeting the core requirement.
    """
    mock_client = MagicMock()
    mock_init_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "event": "FOMC Statement",
            "impact": "critical",
            "time": "2024-01-01T14:00:00.000Z",
            "currency": "USD",
            "country": "US"
        },
        {
            "event": "Non-Farm Employment Change",
            "impact": "high",
            "time": "2024-01-01T13:30:00.000Z",
            "currency": "USD",
            "country": "US"
        }
    ]
    mock_client.get.return_value = mock_response

    provider = MetaAPIEventProvider(token="test_token")
    events = provider.get_upcoming_events(now, now + timedelta(hours=5))

    assert len(events) == 2

    fomc = next(e for e in events if "FOMC" in e.name)
    assert fomc.category == EventCategory.FOMC
    assert fomc.impact == EventImpact.CRITICAL

    nfp = next(e for e in events if "Non-Farm" in e.name)
    assert nfp.category == EventCategory.NFP
    assert nfp.impact == EventImpact.HIGH

@patch("src.data.event_intelligence.MetaAPIEventProvider._init_client")
def test_metaapi_external_feed_error_handling(mock_init_client, now):
    """Verifies fallback behavior when the external feed is unreachable."""
    mock_client = MagicMock()
    mock_init_client.return_value = mock_client
    mock_client.get.side_effect = Exception("Connection Timeout")

    provider = MetaAPIEventProvider(token="test_token")
    events = provider.get_upcoming_events(now, now + timedelta(hours=5))

    assert events is None  # Should return None on failure to trigger fallback logic

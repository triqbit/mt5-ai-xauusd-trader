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
    GeopoliticalEventProvider,
)
from src.core.config import TradingConfig

@pytest.fixture
def now():
    return datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.macro_pre_event_minutes = {1: 5, 2: 15, 3: 60, 4: 120}
    cfg.macro_post_event_minutes = {1: 5, 2: 30, 3: 120, 4: 240}
    cfg.macro_category_pre_event_minutes = {"FOMC": 180}
    cfg.macro_category_post_event_minutes = {"FOMC": 300}
    return cfg

def test_macro_event_severity_scoring(now):
    # HIGH impact FOMC
    event = MacroEvent(name="FOMC", category=EventCategory.FOMC, impact=EventImpact.HIGH, timestamp=now)
    assert event.severity_score == 0.75  # 3/4 * 1.0

    # CRITICAL Geopolitical
    event = MacroEvent(name="War", category=EventCategory.GEOPOLITICAL, impact=EventImpact.CRITICAL, timestamp=now)
    assert event.severity_score == 1.0  # 4/4 * 1.0

    # HIGH impact USD
    event = MacroEvent(name="USD Data", category=EventCategory.USD, impact=EventImpact.HIGH, timestamp=now)
    assert event.severity_score == 0.68  # 3/4 * 0.9 = 0.675 -> 0.68

def test_event_intelligence_risk_windows(now, mock_config):
    # FOMC in 150 minutes. Default HIGH pre-window is 60m. Overridden default for major is 120m.
    # config override is 180m.
    event = MacroEvent(name="FOMC", category=EventCategory.FOMC, impact=EventImpact.HIGH, timestamp=now + timedelta(minutes=150))
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider], config=mock_config)

    status = intel.get_risk_status(now)
    assert any(e.name == "FOMC" for e in status.active_events)
    assert status.is_blocked is False
    # Major HIGH impact cap is 0.25
    assert status.risk_multiplier == 0.25

    # 50 mins before FOMC, it should be blocked
    status = intel.get_risk_status(now + timedelta(minutes=100))
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0

@patch("src.data.event_intelligence.MetaAPIEventProvider._init_client")
def test_metaapi_provider_mocked(mock_init_client, now):
    mock_client = MagicMock()
    mock_init_client.return_value = mock_client
    mock_get = mock_client.get

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

    provider = MetaAPIEventProvider(token="fake")
    events = provider.get_upcoming_events(now - timedelta(hours=1), now + timedelta(hours=1))

    assert len(events) == 1
    assert events[0].name == "Core CPI m/m"
    assert events[0].category == EventCategory.CPI
    assert events[0].actual == 0.3

def test_fail_safe_behavior(now):
    class BrokenProvider(BaseEventProvider):
        def get_upcoming_events(self, start, end):
            raise Exception("API Down")

    intel = EventIntelligence([BrokenProvider()], fail_safe_blocked=True)
    status = intel.get_risk_status(now)
    assert status.is_blocked is True
    assert "Fail-safe BLOCKING" in status.reason

    intel_pass = EventIntelligence([BrokenProvider()], fail_safe_blocked=False)
    status_pass = intel_pass.get_risk_status(now)
    assert status_pass.is_blocked is False
    assert "Fail-safe PASSING" in status_pass.reason

def test_cache_merging_and_pruning(now):
    event1 = MacroEvent(name="Ev1", category=EventCategory.USD, impact=EventImpact.LOW, timestamp=now - timedelta(days=1))
    event2 = MacroEvent(name="Ev2", category=EventCategory.USD, impact=EventImpact.LOW, timestamp=now + timedelta(minutes=10))

    provider = MockEventProvider([event1])
    intel = EventIntelligence([provider])

    # Initial refresh
    intel.refresh(now)
    assert len(intel._cached_events) == 1

    # New event from provider
    provider.events = [event2]
    intel.refresh(now)

    # Should have both if Ev1 is not stale
    assert len(intel._cached_events) == 2

    # Ev1 becomes stale (stale threshold is now - 2 days)
    # Let's make it older
    event1_old = MacroEvent(name="Ev1", category=EventCategory.USD, impact=EventImpact.LOW, timestamp=now - timedelta(days=3))
    provider.events = [event1_old, event2]
    intel._cached_events = [event1_old, event2]
    intel.refresh(now)

    # Ev1 should be pruned from cache in refresh logic?
    # refresh() filters: (ev.end_timestamp or ev.timestamp) >= stale_threshold
    assert len(intel._cached_events) == 1
    assert intel._cached_events[0].name == "Ev2"

def test_geopolitical_provider_manual(now):
    geo_data = [
        {"name": "Border Tension", "impact": 3, "timestamp": now.isoformat()}
    ]
    provider = GeopoliticalEventProvider(geo_data)
    events = provider.get_upcoming_events(now, now + timedelta(hours=1))
    assert len(events) == 1
    assert events[0].category == EventCategory.GEOPOLITICAL
    assert events[0].impact == EventImpact.HIGH

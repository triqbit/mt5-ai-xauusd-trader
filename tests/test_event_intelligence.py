
import pytest
from datetime import datetime, timedelta, timezone
from src.data.event_intelligence import (
    EconomicEvent, ImpactLevel, EventIntelligence, MockEventProvider, EventManager
)

def test_economic_event_validation():
    event = EconomicEvent(
        name="Non-Farm Payrolls",
        symbol="USD",
        timestamp=datetime.now(timezone.utc),
        impact=ImpactLevel.HIGH
    )
    assert event.is_high_impact is True
    assert event.symbol == "USD"

def test_event_intelligence_risk_window():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    # High impact event: 30m pre, 60m post
    event = EconomicEvent(
        name="FOMC",
        symbol="USD",
        timestamp=now,
        impact=ImpactLevel.HIGH
    )

    # 15 mins before: in window
    assert intel.is_in_risk_window(event, now - timedelta(minutes=15)) is True
    # 45 mins before: out of window
    assert intel.is_in_risk_window(event, now - timedelta(minutes=45)) is False
    # 30 mins after: in window
    assert intel.is_in_risk_window(event, now + timedelta(minutes=30)) is True
    # 90 mins after: out of window
    assert intel.is_in_risk_window(event, now + timedelta(minutes=90)) is False

def test_duration_based_risk_window():
    intel = EventIntelligence()
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=2)

    # Critical event with duration: 60m pre, 120m post
    event = EconomicEvent(
        name="Geopolitical Summit",
        symbol="USD",
        timestamp=start,
        end_timestamp=end,
        impact=ImpactLevel.CRITICAL
    )

    # During the event: in window
    assert intel.is_in_risk_window(event, start + timedelta(hours=1)) is True
    # 30 mins before start: in window (pre-buffer)
    assert intel.is_in_risk_window(event, start - timedelta(minutes=30)) is True
    # 1 hour after end: in window (post-buffer)
    assert intel.is_in_risk_window(event, end + timedelta(hours=1)) is True
    # 3 hours after end: out of window
    assert intel.is_in_risk_window(event, end + timedelta(hours=3)) is False

def test_trading_recommendation_critical():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    event = EconomicEvent(
        name="Emergency Rate Cut",
        symbol="USD",
        timestamp=now,
        impact=ImpactLevel.CRITICAL
    )

    rec = intel.get_trading_recommendation([event], now)
    assert rec["block_execution"] is True
    assert rec["position_size_multiplier"] == 0.0
    assert "CRITICAL" in rec["reason"]

def test_trading_recommendation_high():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    event = EconomicEvent(
        name="CPI",
        symbol="USD",
        timestamp=now,
        impact=ImpactLevel.HIGH
    )

    rec = intel.get_trading_recommendation([event], now)
    assert rec["block_execution"] is False
    assert rec["position_size_multiplier"] == 0.5
    assert "HIGH" in rec["reason"]

def test_event_manager_caching_and_fallback():
    mock_events = [
        EconomicEvent(
            name="Test Event",
            symbol="USD",
            timestamp=datetime.now(timezone.utc),
            impact=ImpactLevel.MEDIUM
        )
    ]
    provider = MockEventProvider(mock_events)
    manager = EventManager(provider)

    manager.refresh_events()
    assert len(manager._cached_events) == 1

    # Test recommendation
    rec = manager.get_current_recommendation()
    assert rec["position_size_multiplier"] == 0.75

def test_event_manager_error_fallback():
    class FailingProvider:
        def fetch_events(self, start, end):
            raise Exception("API Down")

    manager = EventManager(FailingProvider()) # type: ignore
    # Should not raise exception
    manager.refresh_events()
    assert manager._cached_events == []

def test_timezone_naive_input_handling():
    intel = EventIntelligence()
    now_naive = datetime.now()
    event = EconomicEvent(
        name="Test",
        symbol="USD",
        timestamp=datetime.now(timezone.utc),
        impact=ImpactLevel.HIGH
    )
    # Should not raise TypeError when comparing naive and aware
    try:
        intel.is_in_risk_window(event, now_naive)
    except TypeError:
        pytest.fail("is_in_risk_window raised TypeError on naive datetime")

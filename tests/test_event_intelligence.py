"""
Tests for Event Intelligence module.
"""
from datetime import datetime, timedelta

import pytest

from src.data.event_intelligence import (
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MockEventProvider,
)


def test_event_impact_comparison():
    assert EventImpact.LOW < EventImpact.MEDIUM
    assert EventImpact.MEDIUM < EventImpact.HIGH
    assert EventImpact.HIGH < EventImpact.CRITICAL
    assert EventImpact.CRITICAL >= EventImpact.HIGH
    assert EventImpact.LOW <= EventImpact.LOW


def test_active_events():
    intel = EventIntelligence()
    now = datetime.utcnow()

    events = [
        MacroEvent(
            name="Past Event",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now - timedelta(hours=2),
        ),
        MacroEvent(
            name="Active Event",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now,
        ),
        MacroEvent(
            name="Future Event",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now + timedelta(hours=2),
        ),
    ]
    intel.refresh_events(events)

    active = intel.get_active_events(now)
    assert len(active) == 1
    assert active[0].name == "Active Event"


def test_risk_multiplier():
    intel = EventIntelligence()
    now = datetime.utcnow()

    # Critical event should block trading (multiplier 0.0)
    intel.refresh_events([
        MacroEvent(
            name="NFP",
            symbol="USD",
            impact=EventImpact.CRITICAL,
            timestamp=now,
        )
    ])
    assert intel.get_risk_multiplier("XAUUSD", now) == 0.0
    assert intel.is_trading_blocked("XAUUSD", now) is True

    # High event should reduce position (multiplier 0.5)
    intel.refresh_events([
        MacroEvent(
            name="CPI",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now,
        )
    ])
    assert intel.get_risk_multiplier("XAUUSD", now) == 0.5
    assert intel.is_trading_blocked("XAUUSD", now) is False

    # No events should have multiplier 1.0
    intel.refresh_events([])
    assert intel.get_risk_multiplier("XAUUSD", now) == 1.0


def test_geopolitical_risk():
    intel = EventIntelligence()
    now = datetime.utcnow()

    intel.refresh_events([
        MacroEvent(
            name="War",
            symbol="ALL",
            impact=EventImpact.HIGH,
            timestamp=now,
            is_geopolitical=True,
        )
    ])
    # Should affect any symbol
    assert intel.get_risk_multiplier("EURJPY", now) == 0.5


def test_mock_provider():
    events = MockEventProvider.get_upcoming_events()
    assert len(events) > 0
    assert any(e.impact == EventImpact.CRITICAL for e in events)

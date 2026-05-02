"""
Tests for Macro Event Intelligence System
"""
from datetime import datetime, timedelta, timezone
import pytest
from src.data.event_intelligence import EventIntelligence, MacroEvent, EventImpact

def test_macro_event_validation():
    event = MacroEvent(
        name="CPI",
        impact=EventImpact.HIGH,
        symbol="USD",
        timestamp=datetime.now(timezone.utc)
    )
    assert event.name == "CPI"
    assert event.impact == EventImpact.HIGH

def test_risk_window_detection():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    # Add a high impact event 10 minutes from now
    event = MacroEvent(
        name="NFP",
        impact=EventImpact.HIGH,
        symbol="USD",
        timestamp=now + timedelta(minutes=10)
    )
    intel.add_event(event)

    # Should be blocked (default pre-window is 30 mins)
    assert intel.is_execution_blocked(high_impact_pre=30, high_impact_post=30) is True

    # 40 minutes from now, it should NOT be blocked
    # Mocking 'now' would be better but let's test logic with window parameters
    assert intel.is_execution_blocked(high_impact_pre=5, high_impact_post=5) is False

def test_risk_multiplier():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    # Medium impact event 10 mins from now
    event = MacroEvent(
        name="Consumer Sentiment",
        impact=EventImpact.MEDIUM,
        symbol="USD",
        timestamp=now + timedelta(minutes=10)
    )
    intel.add_event(event)

    # Multiplier should be 0.5
    assert intel.get_risk_multiplier(med_impact_pre=15, med_impact_post=15) == 0.5

    # High impact event also 10 mins from now
    event_high = MacroEvent(
        name="FOMC",
        impact=EventImpact.HIGH,
        symbol="USD",
        timestamp=now + timedelta(minutes=10)
    )
    intel.add_event(event_high)

    # High impact takes precedence -> 0.0
    assert intel.get_risk_multiplier(med_impact_pre=15, med_impact_post=15) == 0.0

def test_fallback_behavior():
    intel = EventIntelligence()
    # No events added
    assert intel.is_execution_blocked() is False
    assert intel.get_risk_multiplier() == 1.0
    assert intel.fetch_events() is True

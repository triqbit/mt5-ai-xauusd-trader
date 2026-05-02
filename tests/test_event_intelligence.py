"""
Tests for Macro Event Intelligence System
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
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

    # Use tighter window where 10 mins is outside
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

def test_symbol_filtering():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)

    # JPY event should NOT block USD trading
    event_jpy = MacroEvent(
        name="BOJ Rate Decision",
        impact=EventImpact.HIGH,
        symbol="JPY",
        timestamp=now + timedelta(minutes=10)
    )
    intel.add_event(event_jpy)

    # Should NOT be blocked for USD
    assert intel.get_active_risk_impact(target_symbol="USD") == EventImpact.LOW

    # ALL event SHOULD block
    event_all = MacroEvent(
        name="Global Risk Event",
        impact=EventImpact.HIGH,
        symbol="ALL",
        timestamp=now + timedelta(minutes=10)
    )
    intel.add_event(event_all)
    assert intel.get_active_risk_impact(target_symbol="USD") == EventImpact.HIGH

@patch("httpx.get")
def test_fetch_and_normalization(mock_get):
    mock_response = mock_get.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "title": "Core CPI m/m",
            "country": "USD",
            "date": "2024-05-02T08:30:00-04:00",
            "impact": "High",
            "forecast": "0.3%",
            "previous": "0.4%"
        },
        {
            "title": "Unemployment Claims",
            "country": "USD",
            "date": "2024-05-02T08:30:00-04:00",
            "impact": "Medium",
            "actual": "210K"
        }
    ]

    intel = EventIntelligence()
    assert intel.fetch_events() is True
    assert len(intel.events) == 2

    cpi = intel.events[0]
    assert cpi.name == "Core CPI m/m"
    assert cpi.impact == EventImpact.HIGH
    assert cpi.forecast == 0.3
    assert cpi.previous == 0.4

    claims = intel.events[1]
    assert claims.impact == EventImpact.MEDIUM
    assert claims.actual == 210.0

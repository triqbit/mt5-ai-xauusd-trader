"""
Unit tests for the EventIntelligence module.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.data.event_intelligence import EventIntelligence, EventSeverity, MacroEvent


def test_macro_event_is_active():
    now = datetime.now(timezone.utc)
    # Event starting in 30 mins, with 60 min pre-window
    event = MacroEvent(
        name="Test Event",
        symbol="USD",
        timestamp=now + timedelta(minutes=30),
        severity=EventSeverity.HIGH,
        impact_description="Test impact",
        pre_event_window_mins=60,
        post_event_window_mins=60,
    )
    assert event.is_active is True
    assert event.is_imminent is True

    # Event in the past, but within post-window
    past_event = MacroEvent(
        name="Past Event",
        symbol="USD",
        timestamp=now - timedelta(minutes=30),
        severity=EventSeverity.HIGH,
        impact_description="Test impact",
        pre_event_window_mins=60,
        post_event_window_mins=60,
    )
    assert past_event.is_active is True
    assert past_event.is_imminent is False

    # Event far in the future
    future_event = MacroEvent(
        name="Future Event",
        symbol="USD",
        timestamp=now + timedelta(hours=5),
        severity=EventSeverity.HIGH,
        impact_description="Test impact",
        pre_event_window_mins=60,
        post_event_window_mins=60,
    )
    assert future_event.is_active is False


def test_event_intelligence_fetch():
    intel = EventIntelligence()
    success = intel.fetch_events()
    assert success is True
    assert len(intel.get_active_events()) > 0


def test_event_intelligence_blocking():
    intel = EventIntelligence()
    # Mock events to include a high severity active event
    now = datetime.now(timezone.utc)
    high_event = MacroEvent(
        name="High Impact",
        symbol="USD",
        timestamp=now,
        severity=EventSeverity.HIGH,
        impact_description="Blocking",
    )
    intel._events = [high_event]

    assert intel.should_block_execution() is True
    assert intel.get_risk_multiplier() == 0.25


def test_event_intelligence_critical_blocking():
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)
    critical_event = MacroEvent(
        name="Critical Impact",
        symbol="USD",
        timestamp=now,
        severity=EventSeverity.CRITICAL,
        impact_description="Blocking",
    )
    intel._events = [critical_event]

    assert intel.should_block_execution() is True
    assert intel.get_risk_multiplier() == 0.0


def test_event_intelligence_no_active_events():
    intel = EventIntelligence()
    intel._events = []
    assert intel.should_block_execution() is False
    assert intel.get_risk_multiplier() == 1.0


def test_event_intelligence_fallback_behavior():
    intel = EventIntelligence()
    with patch.object(intel, "_get_mocked_events", side_effect=Exception("API Error")):
        success = intel.fetch_events()
        assert success is False
        assert intel._fallback_mode is True
        assert intel.should_block_execution() is False
        assert intel.get_risk_multiplier() == 1.0

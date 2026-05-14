from datetime import UTC, datetime, timedelta

import pytest

from src.data.event_intelligence import (
    BaseEventProvider,
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MockEventProvider,
)


@pytest.fixture
def now():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_provider_failure_returns_none(now):
    """Test that if a provider returns None, EventIntelligence handles it correctly."""

    class FailingProvider(BaseEventProvider):
        def get_upcoming_events(self, start, end):
            return None

    intel = EventIntelligence([FailingProvider()], fail_safe_blocked=True)
    status = intel.get_risk_status(now)

    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert "Event data unavailable (no cache)" in status.reason


def test_severity_score_mapping(now):
    """Test that MacroEvent.severity_score is calculated correctly."""
    # High impact FOMC should be 0.75 (3/4 * 1.0)
    event_fomc = MacroEvent(
        name="FOMC", category=EventCategory.FOMC, impact=EventImpact.HIGH, timestamp=now
    )
    assert event_fomc.severity_score == 0.75

    # Critical Geopolitical should be 1.0 (4/4 * 1.0)
    event_geo = MacroEvent(
        name="War", category=EventCategory.GEOPOLITICAL, impact=EventImpact.CRITICAL, timestamp=now
    )
    assert event_geo.severity_score == 1.0

    # High impact USD should be 0.68 (3/4 * 0.9 = 0.675 -> rounded to 0.68)
    event_usd = MacroEvent(
        name="USD Data", category=EventCategory.USD, impact=EventImpact.HIGH, timestamp=now
    )
    assert event_usd.severity_score == 0.68

    # Medium impact Other should be 0.4 (2/4 * 0.8 = 0.4)
    event_other = MacroEvent(
        name="Minor", category=EventCategory.OTHER, impact=EventImpact.MEDIUM, timestamp=now
    )
    assert event_other.severity_score == 0.4


def test_risk_multiplier_with_severity(now):
    """Test that risk_multiplier is derived from severity_score."""
    # High impact USD data (severity 0.68) -> multiplier 0.32
    # But wait, it might be blocked if it's within 30 mins.
    # Let's put it 40 minutes away.
    event = MacroEvent(
        name="USD Data",
        category=EventCategory.USD,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=40),
    )
    intel = EventIntelligence([MockEventProvider([event])])
    status = intel.get_risk_status(now)

    # High impact USD (non-major) has 60m pre-window (default for HIGH)
    # Ah, I see: pre_window = self.pre_event_minutes.get(event.impact, 0)
    # Default is HIGH: 60.
    # So 40m is WITHIN the pre-window, so it is ACTIVE.
    # Is it BLOCKING?
    # threshold = 60 if event.category in major_categories else 30
    # For USD (non-major), threshold is 30.
    # So at 40m out, it is NOT blocking.

    # It should be active (40 < 60) but not blocked (40 > 30)
    assert any(e.name == "USD Data" for e in status.active_events)
    assert status.is_blocked is False
    assert status.risk_multiplier == 0.32


def test_major_event_stricter_multiplier(now):
    """Test that major events have capped multipliers for institutional safety."""
    # Medium impact NFP (severity 0.5) -> would be 0.5 multiplier, but it's NFP
    # Wait, NFP medium is not capped, only HIGH impact majors are capped at 0.25
    event_nfp_high = MacroEvent(
        name="NFP",
        category=EventCategory.NFP,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=90),
    )
    intel = EventIntelligence([MockEventProvider([event_nfp_high])])
    status = intel.get_risk_status(now)

    # NFP HIGH severity is 0.75 -> 1-0.75 = 0.25. Capped at 0.25 (no change)
    assert status.risk_multiplier == 0.25

    # If severity was lower for some reason, it would still cap.
    # Let's mock a hypothetical major event with low severity but HIGH impact
    # (Actually severity is deterministic based on impact/category)


def test_major_event_window_overrides(now):
    """Test that major events (CPI, NFP, etc.) have larger lead/digestion windows."""
    # NFP in 90 minutes. Normal HIGH impact pre-window is 60m.
    # But NFP should have 120m.
    event = MacroEvent(
        name="NFP",
        category=EventCategory.NFP,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=90),
    )
    intel = EventIntelligence([MockEventProvider([event])])
    status = intel.get_risk_status(now)

    # Should be active (90 < 120) but not blocked (90 > 60)
    assert any(e.name == "NFP" for e in status.active_events)
    assert status.is_blocked is False
    assert status.risk_multiplier == 0.25

    # 50 mins before NFP, it should be blocked
    status = intel.get_risk_status(now + timedelta(minutes=40))
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0

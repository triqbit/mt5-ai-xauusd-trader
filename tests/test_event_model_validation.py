"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_event_model_validation.py

Tests for MacroEvent and RiskStatus schemas and validation.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.core.constants import EventCategory, EventImpact
from src.data.event_models import MacroEvent, RiskStatus


def test_macro_event_timestamps():
    """Verify UTC conversion and default duration assignment."""
    # Input without timezone
    ts = datetime(2025, 1, 1, 12, 0, 0)
    event = MacroEvent(
        name="CPI",
        category=EventCategory.CPI,
        impact=EventImpact.HIGH,
        timestamp=ts
    )

    assert event.timestamp.tzinfo == UTC
    assert event.end_timestamp is not None
    assert event.end_timestamp == event.timestamp + timedelta(hours=1)

def test_macro_event_invalid_end_time():
    """Verify end_time must be after start_time."""
    ts = datetime.now(UTC)
    with pytest.raises(ValidationError):
        MacroEvent(
            name="Fail",
            category=EventCategory.CPI,
            impact=EventImpact.LOW,
            timestamp=ts,
            end_timestamp=ts - timedelta(minutes=1)
        )

def test_risk_status_block_consistency():
    """Verify that is_blocked=True forces risk_multiplier=0.0."""
    # Case 1: is_blocked=True, multiplier=1.0 -> should be auto-corrected to 0.0
    status = RiskStatus(
        is_blocked=True,
        risk_multiplier=1.0,
        reason="Market crash"
    )
    assert status.risk_multiplier == 0.0

    # Case 2: is_blocked=True but no reason -> should raise error
    with pytest.raises(ValidationError) as exc:
        RiskStatus(
            is_blocked=True,
            risk_multiplier=0.0,
            reason=None
        )
    assert "blocked risk status must provide a reason" in str(exc.value).lower()

def test_risk_status_frozen():
    """Verify RiskStatus is immutable."""
    status = RiskStatus(is_blocked=False, risk_multiplier=1.0)
    with pytest.raises(ValidationError):
        status.is_blocked = True # type: ignore

def test_risk_status_extra_forbid():
    """Verify extra fields are forbidden."""
    with pytest.raises(ValidationError):
        RiskStatus(
            is_blocked=False,
            risk_multiplier=1.0,
            extra_field="fail" # type: ignore
        )

import csv
from datetime import UTC, datetime, timedelta

import pytest

from src.data.event_intelligence import (
    CSVEventProvider,
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MockEventProvider,
)


@pytest.fixture
def now():
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_csv_provider_robust_parsing(tmp_path, now):
    """Test CSVEventProvider with mixed impact strings and various timestamps."""
    csv_file = tmp_path / "events.csv"
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "category", "impact", "timestamp", "end_timestamp", "actual"])
        # String impact, standard ISO timestamp
        writer.writerow(
            ["Event 1", "USD", "high", "2024-01-01T12:00:00", "2024-01-01T13:00:00", "0.5"]
        )
        # Integer impact, space-separated timestamp
        writer.writerow(["Event 2", "CPI", "2", "2024-01-01 14:00:00", "", ""])
        # Mixed case impact
        writer.writerow(["Event 3", "NFP", "CRITICAL", "2024-01-01 10:00:00Z", "", ""])

    provider = CSVEventProvider(str(csv_file))
    events = provider.get_upcoming_events(now - timedelta(days=1), now + timedelta(days=1))

    assert len(events) == 3

    # Event 1: high -> HIGH (3)
    e1 = next(e for e in events if e.name == "Event 1")
    assert e1.impact == EventImpact.HIGH
    assert e1.timestamp == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert e1.actual == 0.5

    # Event 2: 2 -> MEDIUM (2)
    e2 = next(e for e in events if e.name == "Event 2")
    assert e2.impact == EventImpact.MEDIUM
    assert e2.timestamp == datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC)

    # Event 3: CRITICAL -> CRITICAL (4)
    e3 = next(e for e in events if e.name == "Event 3")
    assert e3.impact == EventImpact.CRITICAL
    assert e3.timestamp == datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)


def test_risk_multiplier_decay(now):
    """Test that the risk multiplier decays linearly during the post-event window."""
    # NFP is a major event. High impact NFP has 180m post-window.
    # It blocks for the first 60m.

    # Let's check 120m after end.
    # event_end = now - 120m
    # event_start = now - 180m (1h duration)
    event_time = now - timedelta(minutes=180)
    event = MacroEvent(
        name="NFP",
        category=EventCategory.NFP,
        impact=EventImpact.HIGH,
        timestamp=event_time,
    )

    # event_end = now - 120m
    # elapsed = 120m
    # post_window = 180m
    # decay_factor = 120 / 180 = 0.666...
    # base_mult = 0.25 (since it is NFP HIGH)
    # expected_mult = 0.25 + (1.0 - 0.25) * 0.666... = 0.25 + 0.75 * 0.666... = 0.25 + 0.5 = 0.75

    intel = EventIntelligence([MockEventProvider([event])])
    status = intel.get_risk_status(now)

    assert status.is_blocked is False  # 120m elapsed > 60m, no longer blocking
    assert status.risk_multiplier == 0.75


def test_risk_multiplier_decay_full_recovery(now):
    """Test that the risk multiplier fully recovers to 1.0 after the post-event window."""
    event_time = now - timedelta(minutes=300)
    event = MacroEvent(
        name="USD Data",
        category=EventCategory.USD,
        impact=EventImpact.HIGH,
        timestamp=event_time,
    )
    # Default duration 1h -> ended 240m ago.
    # post_window for HIGH is 120m.
    # 240m > 120m, should be fully recovered.

    intel = EventIntelligence([MockEventProvider([event])])
    status = intel.get_risk_status(now)

    assert status.risk_multiplier == 1.0
    assert len(status.active_events) == 0


def test_guess_category_refinements():
    """Test the newly added keywords in MetaAPIEventProvider._guess_category."""
    from src.data.event_intelligence import MetaAPIEventProvider

    provider = MetaAPIEventProvider(token="fake")

    assert provider._guess_category("Core PCE Price Index") == EventCategory.CPI
    assert provider._guess_category("Consumer Price Index (CPI) y/y") == EventCategory.CPI
    assert provider._guess_category("Nonfarm Payrolls") == EventCategory.NFP

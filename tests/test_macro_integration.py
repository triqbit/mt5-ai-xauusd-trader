from datetime import UTC, datetime, timedelta

import pytest

from src.core.config import TradingConfig
from src.core.schemas import TradeSignal
from src.data.event_intelligence import (
    EventCategory,
    EventImpact,
    EventIntelligence,
    MacroEvent,
    MetaAPIEventProvider,
    MockEventProvider,
)
from src.trading.execution_filter import ExecutionFilter


@pytest.fixture
def now():
    # 2023-01-02 is a Monday, avoiding SESSION_CLOSED issues
    return datetime(2023, 1, 2, 12, 0, 0, tzinfo=UTC)

def test_cpi_major_event_window(now):
    # CPI in 90 minutes. Before enhancement, it had 60m pre-window.
    # Now it should have 120m pre-window as a major event.
    event = MacroEvent(
        name="US CPI",
        category=EventCategory.CPI,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=90)
    )
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider])

    status = intel.get_risk_status(now)
    # CPI is a major event, so it gets a stricter multiplier (0.25) even if not blocked yet
    assert status.risk_multiplier == 0.25
    assert len(status.active_events) == 1

    # Check at 50m (should be blocked as it's within 60m block window for HIGH major events)
    status = intel.get_risk_status(now + timedelta(minutes=40))
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0

def test_new_keywords_opec_terror_attack():
    provider = MetaAPIEventProvider(token="fake")
    assert provider._guess_category("OPEC Meeting Outcome") == EventCategory.USD_MACRO
    assert provider._guess_category("Terror Attack Alert") == EventCategory.GEOPOLITICAL
    assert provider._guess_category("Cyber Attack on Infrastructure") == EventCategory.GEOPOLITICAL

def test_execution_filter_macro_gate(now):
    event = MacroEvent(
        name="FOMC Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=15)
    )
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider])

    # Mock config
    config = TradingConfig(MT5_PASSWORD="fake", MT5_SERVER="fake")

    filt = ExecutionFilter(config=config, event_intelligence=intel)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2015.0,
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.8,
        timestamp=now
    )

    decision = filt.validate(signal)

    assert decision.is_approved is False
    assert decision.blocked_by == "MACRO_EVENT"
    assert decision.trace["macro_event"]["passed"] is False
    assert decision.trace["macro_event"]["is_blocked"] is True

def test_execution_filter_macro_gate_disabled(now):
    event = MacroEvent(
        name="FOMC Decision",
        category=EventCategory.FOMC,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=15)
    )
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider])

    # Mock config with macro guard disabled
    config = TradingConfig(MT5_PASSWORD="fake", MT5_SERVER="fake", enable_macro_guard=False)

    filt = ExecutionFilter(config=config, event_intelligence=intel)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2015.0,
        lot_size=0.1,
        algorithm="test_algo",
        confidence=0.8,
        timestamp=now
    )

    decision = filt.validate(signal)

    # Should be approved by macro gate (but might be blocked by other layers like ATR)
    # We check specifically the macro_event trace
    assert decision.trace["macro_event"]["passed"] is True
    assert decision.trace["macro_event"]["status"] == "guard_disabled"

def test_event_intelligence_config_integration(now):
    # Test that EventIntelligence uses custom windows from config
    config = TradingConfig(
        MT5_PASSWORD="fake",
        MT5_SERVER="fake",
        macro_pre_event_minutes={3: 100}, # HIGH impact pre-window = 100m
        macro_post_event_minutes={3: 200} # HIGH impact post-window = 200m
    )

    event = MacroEvent(
        name="USD Macro",
        category=EventCategory.USD_MACRO,
        impact=EventImpact.HIGH,
        timestamp=now + timedelta(minutes=90)
    )
    provider = MockEventProvider([event])
    intel = EventIntelligence([provider], config=config)

    assert intel.pre_event_minutes[EventImpact.HIGH] == 100
    assert intel.post_event_minutes[EventImpact.HIGH] == 200

    status = intel.get_risk_status(now)
    assert len(status.active_events) == 1 # Active because 90 < 100

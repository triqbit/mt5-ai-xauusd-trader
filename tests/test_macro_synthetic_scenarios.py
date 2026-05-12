"""
Tests for MacroScenarioBuilder and SystemContextBuilder in synthetic_data.py.
"""

import pandas as pd

from src.core.constants import EventCategory, EventImpact
from src.data.event_models import MacroEvent, RiskStatus
from src.utils.synthetic_data import MacroScenarioBuilder, SystemContextBuilder


def test_macro_scenario_builder_nfp():
    builder = MacroScenarioBuilder()
    event = builder.nfp_shock()

    assert isinstance(event, MacroEvent)
    assert event.name == "Non-Farm Payrolls"
    assert event.category == EventCategory.NFP
    assert event.impact == EventImpact.HIGH
    assert "USD" in event.symbol_impact
    assert "XAUUSD" in event.symbol_impact


def test_macro_scenario_builder_fomc():
    builder = MacroScenarioBuilder()
    event = builder.fomc_meeting()

    assert isinstance(event, MacroEvent)
    assert event.name == "FOMC Rate Decision"
    assert event.category == EventCategory.FOMC
    assert event.impact == EventImpact.CRITICAL


def test_macro_scenario_builder_geopolitical():
    builder = MacroScenarioBuilder()
    event = builder.geopolitical_crisis()

    assert isinstance(event, MacroEvent)
    assert event.category == EventCategory.GEOPOLITICAL
    assert event.impact == EventImpact.HIGH


def test_system_context_builder_normal():
    builder = SystemContextBuilder(seed=42)
    df, events, risk = builder.normal_trading()

    assert isinstance(df, pd.DataFrame)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert len(df) == 200
    assert events == []
    assert isinstance(risk, RiskStatus)
    assert risk.is_blocked is False
    assert risk.risk_multiplier == 1.0


def test_system_context_builder_nfp():
    builder = SystemContextBuilder(seed=42)
    df, events, risk = builder.high_impact_macro_event()

    assert len(df) == 200
    assert len(events) == 1
    assert events[0].category == EventCategory.NFP
    assert risk.is_blocked is True
    assert risk.risk_multiplier == 0.0
    assert risk.active_events == events


def test_system_context_builder_fomc():
    builder = SystemContextBuilder(seed=42)
    df, events, risk = builder.extreme_volatility_with_risk_block()

    assert len(df) == 200
    assert len(events) == 1
    assert events[0].category == EventCategory.FOMC
    assert risk.is_blocked is True
    assert risk.risk_multiplier == 0.0
    assert risk.active_events == events
    assert "FOMC" in risk.reason

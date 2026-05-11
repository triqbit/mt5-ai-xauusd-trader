"""
Tests for macro and system-context synthetic scenario builders.
"""

from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core.constants import EventCategory, EventImpact, SignalDirection
from src.models.regime_detector import MarketRegime
from src.utils.synthetic_data import (
    MacroScenarioBuilder,
    SystemContextBuilder,
    SystemScenarioContext,
)


@pytest.fixture
def macro_builder():
    return MacroScenarioBuilder(seed=42)

@pytest.fixture
def system_builder():
    return SystemContextBuilder(seed=42)

def test_nfp_shock(macro_builder):
    events = macro_builder.nfp_shock()
    assert len(events) == 1
    event = events[0]
    assert event.name == "Non-Farm Payrolls"
    assert event.category == EventCategory.NFP
    assert event.impact == EventImpact.HIGH
    assert "XAUUSD" in event.symbol_impact

def test_fomc_policy_day(macro_builder):
    events = macro_builder.fomc_policy_day()
    assert len(events) == 2
    categories = [e.category for e in events]
    assert EventCategory.FOMC in categories
    assert EventCategory.RATES in categories
    assert all(e.impact == EventImpact.CRITICAL for e in events)

def test_geopolitical_tension(macro_builder):
    ts = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    events = macro_builder.geopolitical_tension(timestamp=ts)
    assert len(events) == 1
    event = events[0]
    assert event.category == EventCategory.GEOPOLITICAL
    assert event.timestamp < ts
    assert event.end_timestamp > ts

def test_extreme_risk_status(macro_builder):
    status = macro_builder.extreme_risk_status()
    assert status.is_blocked is True
    assert status.risk_multiplier == 0.0
    assert len(status.blocking_events) == 2

def test_modulated_risk_status(macro_builder):
    status = macro_builder.modulated_risk_status(multiplier=0.4)
    assert status.is_blocked is False
    assert status.risk_multiplier == 0.4
    assert len(status.active_events) == 2

def test_crisis_scenario_context(system_builder):
    ctx = system_builder.create_crisis_scenario()
    assert isinstance(ctx, SystemScenarioContext)
    assert not ctx.ohlcv.empty
    assert ctx.signal.direction == SignalDirection.BUY
    assert ctx.macro_risk.is_blocked is True
    assert ctx.model_health["drift"] > 0.3
    assert ctx.regime.label == MarketRegime.VOLATILE_BREAKOUT

def test_bull_run_scenario_context(system_builder):
    ctx = system_builder.create_bull_run_scenario()
    assert isinstance(ctx, SystemScenarioContext)
    assert not ctx.ohlcv.empty
    assert ctx.signal.direction == SignalDirection.BUY
    assert ctx.macro_risk.is_blocked is False
    assert ctx.model_health["drift"] < 0.3
    assert ctx.regime.label == MarketRegime.TRENDING

def test_system_context_determinism(system_builder):
    ctx1 = system_builder.create_crisis_scenario()
    ctx2 = SystemContextBuilder(seed=42).create_crisis_scenario()

    pd.testing.assert_frame_equal(ctx1.ohlcv, ctx2.ohlcv)
    assert ctx1.signal == ctx2.signal
    assert ctx1.macro_risk == ctx2.macro_risk
    assert ctx1.model_health == ctx2.model_health
    assert ctx1.regime == ctx2.regime

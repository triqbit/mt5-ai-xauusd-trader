"""
Unit and integration tests for Macro Event Intelligence.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.core.config import TradingConfig
from src.data.event_intelligence import EventImpact, EventIntelligence, MacroEvent
from src.trading.risk_manager import RiskManager, TradeSignal


@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.enable_macro_filter = True
    cfg.macro_event_high_pre = 30
    cfg.macro_event_high_post = 60
    cfg.risk_per_trade = 0.01
    cfg.max_positions = 3
    cfg.max_daily_loss = 0.05
    return cfg


def test_macro_event_window_logic():
    now = datetime.now(timezone.utc)
    event = MacroEvent(
        name="Test Event",
        symbol="USD",
        impact=EventImpact.HIGH,
        timestamp=now,
        pre_window_mins=30,
        post_window_mins=60
    )

    assert event.is_active(now)
    assert event.is_active(now - timedelta(minutes=30))
    assert event.is_active(now + timedelta(minutes=60))
    assert not event.is_active(now - timedelta(minutes=31))
    assert not event.is_active(now + timedelta(minutes=61))


def test_event_intelligence_blocking(mock_config):
    now = datetime.now(timezone.utc)
    intel = EventIntelligence(config=mock_config)

    # Manually set events
    intel.events = [
        MacroEvent(
            name="High Impact USD",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now,
            pre_window_mins=30,
            post_window_mins=60
        )
    ]

    assert intel.should_block_execution("XAUUSD", now) is True
    assert intel.should_block_execution("EURUSD", now) is True
    assert intel.should_block_execution("GBPUSD", now + timedelta(minutes=61)) is False


def test_event_intelligence_risk_multiplier(mock_config):
    now = datetime.now(timezone.utc)
    intel = EventIntelligence(config=mock_config)

    intel.events = [
        MacroEvent(
            name="Medium Impact Gold",
            symbol="XAUUSD",
            impact=EventImpact.MEDIUM,
            timestamp=now,
            pre_window_mins=15,
            post_window_mins=30
        )
    ]

    assert intel.get_risk_multiplier("XAUUSD", now) == 0.5
    assert intel.get_risk_multiplier("EURUSD", now) == 1.0  # Different symbol


def test_risk_manager_integration(mock_config):
    now = datetime.now(timezone.utc)
    intel = EventIntelligence(config=mock_config)
    intel.events = [
        MacroEvent(
            name="FOMC",
            symbol="USD",
            impact=EventImpact.HIGH,
            timestamp=now,
            pre_window_mins=30,
            post_window_mins=60
        )
    ]

    risk = RiskManager(
        config=mock_config,
        account_balance=10000.0,
        event_intel=intel
    )

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
        timestamp=now
    )

    # Should be rejected due to HIGH impact event
    assert risk.approve(signal) is False


def test_risk_manager_size_reduction(mock_config):
    now = datetime.now(timezone.utc)
    intel = EventIntelligence(config=mock_config)
    intel.events = [
        MacroEvent(
            name="Consumer Confidence",
            symbol="USD",
            impact=EventImpact.MEDIUM,
            timestamp=now,
            pre_window_mins=30,
            post_window_mins=60
        )
    ]

    risk = RiskManager(
        config=mock_config,
        account_balance=10000.0,
        event_intel=intel
    )

    # Mock size_position calculation
    # Balance 10000, risk 1% = 100 risk capital
    # Multiplier 0.5 should make it 50 risk capital
    # If we ignore Kelly and just look at risk_capital:
    # (risk_capital * kelly) / (loss * pip)
    # We want to verify risk_capital is reduced.

    risk.size_position("XAUUSD", 0.5, 10, 10) # No events active in this call if we don't mock now()

    # We need to ensure size_position uses the right time.
    # In the implementation it uses datetime.now(timezone.utc)
    # We'll rely on the fact that 'now' is very close to current time.

    # Actually, let's just check if it's less than a theoretical maximum
    # risk_capital = 10000 * 0.01 * 0.5 = 50.
    # lot = (50 * kelly) / (avg_loss * pip)

    lot_size = risk.size_position("XAUUSD", 0.6, 2.0, 1.0)
    # kelly = (0.6 * 2.0 - 0.4 * 1.0) / 2.0 = 0.4
    # capped kelly = 0.25
    # risk_capital = 10000 * 0.01 * 0.5 = 50
    # lot = (50 * 0.25) / (1.0 * 1.0) = 12.5

    assert lot_size == 12.5

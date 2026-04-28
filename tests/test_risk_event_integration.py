"""
Integration tests for EventIntelligence and RiskManager.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.core.config import TradingConfig
from src.data.event_intelligence import EventIntelligence, EventSeverity, MacroEvent
from src.trading.risk_manager import RiskManager, TradeSignal


@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="password",
        mt5_server="server",
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=3,
    )


def test_risk_manager_with_event_intel_blocking(config):
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)
    high_event = MacroEvent(
        name="High Impact",
        symbol="USD",
        timestamp=now,
        severity=EventSeverity.HIGH,
        impact_description="Blocking",
    )
    intel._events = [high_event]

    risk = RiskManager(config, account_balance=10000.0, event_intel=intel)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )

    assert risk.approve(signal) is False


def test_risk_manager_with_event_intel_sizing(config):
    intel = EventIntelligence()
    now = datetime.now(timezone.utc)
    medium_event = MacroEvent(
        name="Medium Impact",
        symbol="USD",
        timestamp=now,
        severity=EventSeverity.MEDIUM,
        impact_description="Sizing reduction",
    )
    intel._events = [medium_event]

    risk = RiskManager(config, account_balance=10000.0, event_intel=intel)

    # Standard sizing without multiplier would be based on risk_per_trade=0.01 (100.0)
    # Medium event multiplier is 0.5, so risk_capital should be 50.0
    # Kelly fraction maxed at 0.25, so 10000 * 0.01 * 0.5 * 0.25 = 12.5
    # avg_loss = 10, lot_size = 12.5 / 10 = 1.25

    lot_size = risk.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=20.0,
        avg_loss=10.0,
    )

    assert lot_size == 1.25


def test_risk_manager_without_event_intel(config):
    risk = RiskManager(config, account_balance=10000.0, event_intel=None)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8,
    )

    assert risk.approve(signal) is True

    lot_size = risk.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=20.0,
        avg_loss=10.0,
    )
    # Standard sizing: 10000 * 0.01 * 0.25 = 25.0. 25.0 / 10 = 2.5
    assert lot_size == 2.5

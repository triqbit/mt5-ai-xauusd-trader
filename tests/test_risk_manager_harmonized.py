"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_risk_manager_harmonized.py

Verification of the unified RiskManager.
"""

import datetime

import pytest

from src.core.config import TradingConfig
from src.core.schemas import SignalDirection, TradeSignal
from src.trading.risk_manager import RiskManager


@pytest.fixture
def config():
    return TradingConfig(
        MT5_LOGIN=123456,
        MT5_PASSWORD="dummy_password",
        MT5_SERVER="dummy_server",
        MT5_PATH="C:/terminal.exe",
        symbol="XAUUSD",
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=3,
        max_trades_per_day=10,
        max_losing_streak=5,
        min_confidence=0.6,
        max_drawdown=0.15,
        min_lot_size=0.01,
    )


@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)


@pytest.fixture
def buy_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )


def test_drawdown_breaker(risk_manager, buy_signal):
    # Set peak equity high and current balance low to trigger drawdown
    risk_manager.peak_equity = 20000.0
    risk_manager.balance = 10000.0  # 50% drawdown

    approved = risk_manager.approve(buy_signal)
    assert not approved


def test_daily_loss_limit(risk_manager, buy_signal):
    risk_manager.daily.peak_equity = 10000.0
    risk_manager.daily.realised_pnl = -600.0  # 6% loss

    approved = risk_manager.approve(buy_signal)
    assert not approved


def test_max_positions(risk_manager, buy_signal):
    risk_manager.open_positions = {"XAUUSD": 1, "EURUSD": 2, "GBPUSD": 3}

    approved = risk_manager.approve(buy_signal)
    assert not approved


def test_kelly_position_sizing(risk_manager):
    # Test Kelly sizing
    # size_position(self, symbol, win_rate, avg_win, avg_loss, pip_value=1.0)
    size = risk_manager.size_position("XAUUSD", 0.6, 20.0, 10.0)
    assert size > 0
    assert isinstance(size, float)


def test_full_approval(risk_manager, buy_signal):
    approved = risk_manager.approve(buy_signal)
    assert approved is True

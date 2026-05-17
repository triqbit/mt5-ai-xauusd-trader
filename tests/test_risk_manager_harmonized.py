"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_risk_manager_harmonized.py

Verification of the unified RiskManager with 8-layer cascade.
"""

import datetime
import os

import pytest

from src.core.config import TradingConfig
from src.core.schemas import SignalDirection, TradeSignal
from src.trading.risk_manager import RiskManager
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def config():
    # Use environment variables to satisfy TradingConfig validation
    os.environ["MT5_PASSWORD"] = "dummy_password"
    os.environ["MT5_SERVER"] = "dummy_server"
    return TradingConfig(
        symbol="XAUUSD",
        risk_per_trade=0.01,
        max_daily_loss=0.05,
        max_positions=3,
        max_trades_per_day=10,
        max_losing_streak=5,
        min_confidence=0.6,
        max_drawdown=0.15,
        max_single_direction_pct=0.3,
        max_total_notional_pct=1.0,
        min_lot_size=0.01,
        volatility_high_threshold=1.5,
        volatility_very_high_threshold=2.0,
        volatility_extreme_threshold=3.0,
        max_position_size_pct=0.1
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

@pytest.fixture
def market_data():
    gen = ScenarioGenerator()
    df = gen.generate(n_steps=100, regime="ranging")
    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
    df["close"] = df["close"].ffill() # Ensure no NaNs at the end
    return df

@pytest.fixture
def buy_signal(market_data):
    price = market_data["close"].iloc[-1]
    return TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=price,
        stop_loss=price - 10,
        take_profit=price + 20,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
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
    # Mocking open positions
    risk_manager.open_positions = {
        "XAUUSD": 1,
        "EURUSD": 2,
        "GBPUSD": 3
    }

    approved = risk_manager.approve(buy_signal)
    assert not approved

def test_atr_position_sizing(risk_manager):
    # Size position using Kelly
    size = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.55,
        avg_win=20.0,
        avg_loss=10.0
    )
    assert size > 0
    assert size <= 10.0 # Sanity check for 10000 balance

def test_full_approval(risk_manager, buy_signal):
    approved = risk_manager.approve(buy_signal)
    assert approved

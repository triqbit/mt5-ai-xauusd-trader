"""
Tests for RiskManager using synthetic market scenarios.
"""
import pytest
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig
from src.utils.synthetic_data import ScenarioGenerator

@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="fake",
        mt5_server="fake",
        max_positions=3,
        risk_per_trade=0.01,
        max_daily_loss=0.05
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

@pytest.fixture
def generator():
    return ScenarioGenerator(seed=42)

def test_circuit_breaker_on_drawdown(risk_manager):
    # Simulate a major drawdown
    risk_manager.update_equity(10000.0) # peak
    risk_manager.update_equity(8000.0)  # 20% drawdown (> 15% limit)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False

def test_daily_loss_limit(risk_manager):
    # Simulate $600 loss on $10000 peak equity (6% loss > 5% limit)
    risk_manager.daily.peak_equity = 10000.0
    risk_manager.record_pnl(-600.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    assert risk_manager.approve(signal) is False

def test_position_sizing_with_volatility_spike(risk_manager, generator):
    # Normal volatility
    df_normal = generator.generate_gbm(n_bars=20, sigma=0.001)
    atr_normal = (df_normal["high"] - df_normal["low"]).mean()

    lot_normal = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=2*atr_normal,
        avg_loss=atr_normal,
        pip_value=1.0
    )

    # Volatility spike
    df_spike = generator.generate_volatility_spike(n_bars=20, spike_at=10, sigma_mult=10.0)
    # Get ATR from the spike part (last 10 bars)
    atr_spike = (df_spike["high"] - df_spike["low"]).iloc[-10:].mean()

    lot_spike = risk_manager.size_position(
        symbol="XAUUSD",
        win_rate=0.6,
        avg_win=2*atr_spike,
        avg_loss=atr_spike,
        pip_value=1.0
    )

    # Lot size should be smaller for higher volatility if avg_loss is higher
    assert lot_spike < lot_normal

def test_rejection_on_low_confidence(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4 # below 0.55 default
    )
    assert risk_manager.approve(signal) is False

def test_rejection_on_invalid_symbol(risk_manager):
    signal = TradeSignal(
        symbol="INVALID",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is False

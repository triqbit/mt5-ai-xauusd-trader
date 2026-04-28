"""Tests for src.trading.risk_engine module."""
import pytest
from src.core.config import TradingConfig
from src.trading.risk_engine import RiskEngine
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def risk_engine():
    cfg = TradingConfig(
        mt5_login=123, mt5_password="pw", mt5_server="srv",
        risk_per_trade=0.01,
        daily_loss_halt_pct=0.05,
        drawdown_halt_pct=0.25,
        volatility_extreme_threshold=3.0,
        confidence_threshold=0.6
    )
    return RiskEngine(cfg)

def test_risk_engine_check_signal_allowed(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ensemble", confidence=0.7
    )
    # No drawdown, normal volatility
    assert risk_engine.check_signal(signal, current_drawdown=0.05, atr=1.0, atr_sma=1.0) is True

def test_risk_engine_check_signal_drawdown_halt(risk_engine):
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ensemble", confidence=0.7
    )
    # 26% drawdown exceeds 25% halt
    assert risk_engine.check_signal(signal, current_drawdown=0.26, atr=1.0, atr_sma=1.0) is False

def test_risk_engine_check_signal_daily_loss_halt(risk_engine):
    risk_engine.update_metrics(balance=10000, equity=10000, realized_pnl=-600) # 6% loss
    signal = TradeSignal(
        symbol="XAUUSD", direction=1, entry_price=2300.0,
        stop_loss=2290.0, take_profit=2320.0, lot_size=0.1,
        algorithm="ensemble", confidence=0.7
    )
    assert risk_engine.check_signal(signal, current_drawdown=0.05, atr=1.0, atr_sma=1.0) is False

def test_risk_engine_calculate_position_size_normal(risk_engine):
    # Balance 10000, 1% risk = $100. SL distance = 10 units.
    # Gold: tick_size=0.01, tick_value=0.01 (approx for 0.01 lot -> 1.0 for 1.0 lot)
    # formula: 100 / (10 * (1.0 / 0.01)) = 100 / (10 * 100) = 100 / 1000 = 0.1
    size = risk_engine.calculate_position_size(
        balance=10000.0, stop_loss_dist=10.0,
        current_drawdown=0.05, atr=1.0, atr_sma=1.0,
        tick_value=1.0, tick_size=0.01
    )
    assert size == 0.1

def test_risk_engine_calculate_position_size_cascading(risk_engine):
    # 21% drawdown -> 50% size multiplier
    # 10000 balance, 1% risk = 100. Multiplier 0.5 -> 50 risk capital.
    # SL distance 10 -> size 0.05
    size = risk_engine.calculate_position_size(
        balance=10000.0, stop_loss_dist=10.0,
        current_drawdown=0.21, atr=1.0, atr_sma=1.0,
        tick_value=1.0, tick_size=0.01
    )
    assert size == 0.05

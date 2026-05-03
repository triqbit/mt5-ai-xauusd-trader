"""Tests for src.trading.risk_engine module."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def mock_config():
    config = MagicMock(spec=TradingConfig)
    config.risk_per_trade = 0.01
    config.max_daily_loss = 0.05
    return config

def test_atr_lot_size_normal(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # balance=10000, risk=1%=$100
    # atr=1.0, avg_atr=1.0 -> vol_mult=1.0
    # stop_loss_distance=5.0, tick_value=1.0, tick_size=0.01
    # risk_per_lot = (5.0 / 0.01) * 1.0 = 500
    # lot_size = 100 / 500 = 0.2
    lot_size = engine.calculate_atr_lot_size("XAUUSD", 10000.0, 5.0, 1.0, 1.0, tick_value=1.0, tick_size=0.01)
    assert lot_size == 0.2

def test_atr_lot_size_high_volatility(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # atr=2.1, avg_atr=1.0 -> vol_mult=0.5
    # risk_amount = 100 * 0.5 = 50
    # 50 / 500 = 0.1
    lot_size = engine.calculate_atr_lot_size("XAUUSD", 10000.0, 5.0, 2.1, 1.0, tick_value=1.0, tick_size=0.01)
    assert lot_size == 0.1

def test_atr_lot_size_extreme_volatility(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # atr=3.1, avg_atr=1.0 -> Trading Halted
    lot_size = engine.calculate_atr_lot_size("XAUUSD", 10000.0, 5.0, 3.1, 1.0, tick_value=1.0, tick_size=0.01)
    assert lot_size == 0.0

def test_daily_loss_circuit_breaker(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # Simulate $501 loss (5.01% of 10000)
    engine.update_metrics(9499.0, pnl=-501.0)

    signal = TradeSignal("XAUUSD", 1, 2000.0, 1995.0, 2010.0, 0.1, "test", 0.7)
    assert engine.validate_signal(signal, 1.0, 1.0) is False

def test_consecutive_losses_guard(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    engine.update_metrics(9900.0, pnl=-50.0)
    engine.update_metrics(9850.0, pnl=-50.0)
    engine.update_metrics(9800.0, pnl=-50.0)

    signal = TradeSignal("XAUUSD", 1, 2000.0, 1995.0, 2010.0, 0.1, "test", 0.7)
    assert engine.validate_signal(signal, 1.0, 1.0) is False

def test_drawdown_hard_stop(mock_config):
    engine = RiskEngine(mock_config, 10000.0)
    # Drop to $6900 (31% drawdown)
    engine.update_metrics(6900.0, pnl=-3100.0)

    signal = TradeSignal("XAUUSD", 1, 2000.0, 1995.0, 2010.0, 0.1, "test", 0.7)
    assert engine.validate_signal(signal, 1.0, 1.0) is False

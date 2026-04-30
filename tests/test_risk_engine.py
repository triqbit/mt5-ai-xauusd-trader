"""Tests for RiskEngine."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine, TradeSignal

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.risk_per_trade = 0.01
    cfg.max_positions = 5
    cfg.max_losing_streak = 3
    cfg.confidence_threshold = 0.55
    cfg.drawdown_levels = {1: 0.10, 2: 0.15, 3: 0.20, 4: 0.25, 5: 0.30}
    cfg.daily_loss_levels = {1: 0.02, 2: 0.03, 3: 0.04, 4: 0.05}
    return cfg

def test_risk_engine_approve_signal(mock_config):
    engine = RiskEngine(mock_config, account_balance=10000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )
    assert engine.approve_signal(signal) is True

def test_risk_engine_reject_low_confidence(mock_config):
    engine = RiskEngine(mock_config, account_balance=10000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.5 # Below 0.55
    )
    assert engine.approve_signal(signal) is False

def test_risk_engine_daily_loss_limit(mock_config):
    engine = RiskEngine(mock_config, account_balance=10000.0)
    # Simulate 6% daily loss
    engine.update_performance(current_equity=9400.0, realised_pnl=-600.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ppo",
        confidence=0.7
    )
    assert engine.approve_signal(signal) is False
    assert engine.trading_halted is True

def test_risk_engine_calculate_lot_size(mock_config):
    engine = RiskEngine(mock_config, account_balance=10000.0)

    # risk_amount = balance * risk_per_trade = 10000 * 0.01 = 100
    # risk_per_unit = abs(2300.0 - 2290.0) = 10.0
    # if pip_value is 1.0 (override in call)
    # lot_size = risk_amount / (risk_per_unit * pip_value)
    # 100 / (10 * 1) = 10.0

    # Wait, the code has:
    # max_notional = self.balance * 0.10 = 1000.0
    # notional_value = lot_size * entry_price = 10.0 * 2300.0 = 23000.0
    # 23000.0 > 1000.0
    # lot_size = max(0.01, round(1000.0 / 2300.0, 2)) = 0.43
    # That's why it is 0.43!

    lot = engine.calculate_lot_size("XAUUSD", 2300.0, 2290.0, atr=5.0, pip_value=1.0)
    assert lot == 0.43

def test_risk_engine_drawdown_multiplier(mock_config):
    engine = RiskEngine(mock_config, account_balance=10000.0)
    # Simulate 20% drawdown (Level 3)
    engine.update_performance(current_equity=8000.0)
    assert engine.current_risk_multiplier == 0.5

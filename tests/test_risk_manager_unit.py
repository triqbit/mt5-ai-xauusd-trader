"""
Tests for RiskManager.
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.02
    cfg.max_daily_loss = 0.10
    cfg.max_positions = 5
    return cfg

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(config=mock_config, account_balance=10000.0)

def test_risk_manager_init(risk_manager):
    assert risk_manager.balance == 10000.0
    assert risk_manager.peak_equity == 10000.0
    assert risk_manager.daily.peak_equity == 10000.0

def test_check_circuit_breaker(risk_manager):
    # No drawdown
    assert risk_manager._check_circuit_breaker() is True

    # 10% drawdown
    risk_manager.balance = 9000.0
    assert risk_manager._check_circuit_breaker() is True

    # 16% drawdown
    risk_manager.balance = 8400.0
    assert risk_manager._check_circuit_breaker() is False

def test_check_daily_loss(risk_manager):
    risk_manager.daily.peak_equity = 10000.0
    risk_manager.daily.realised_pnl = -500.0 # 5% loss
    assert risk_manager._check_daily_loss() is True

    risk_manager.daily.realised_pnl = -1500.0 # 15% loss
    assert risk_manager._check_daily_loss() is False

def test_check_max_positions(risk_manager):
    risk_manager.open_positions = {"SYM1": 1, "SYM2": 2, "SYM3": 3, "SYM4": 4}
    assert risk_manager._check_max_positions() is True

    risk_manager.open_positions["SYM5"] = 5
    assert risk_manager._check_max_positions() is False

def test_check_symbol_allocation(risk_manager):
    assert risk_manager._check_symbol_allocation("XAUUSD") is True
    assert risk_manager._check_symbol_allocation("INVALID") is False

def test_check_minimum_confidence(risk_manager):
    assert risk_manager._check_minimum_confidence(0.6) is True
    assert risk_manager._check_minimum_confidence(0.4) is False

def test_check_risk_reward(risk_manager):
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
    # R:R = (2020-2000) / (2000-1990) = 2.0 > 1.5
    assert risk_manager._check_risk_reward(signal) is True

    signal.take_profit = 2010.0 # R:R = 1.0 < 1.5
    assert risk_manager._check_risk_reward(signal) is False

def test_approve_cascade(risk_manager):
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

    # All pass
    assert risk_manager.approve(signal) is True

    # Fail one (confidence)
    signal.confidence = 0.1
    assert risk_manager.approve(signal) is False

def test_size_position(risk_manager):
    # Simple Kelly sizing test
    lot = risk_manager.size_position("XAUUSD", win_rate=0.6, avg_win=20.0, avg_loss=10.0)
    assert lot > 0
    assert isinstance(lot, float)

def test_update_equity(risk_manager):
    risk_manager.update_equity(11000.0)
    assert risk_manager.balance == 11000.0
    assert risk_manager.peak_equity == 11000.0

    risk_manager.update_equity(10500.0)
    assert risk_manager.balance == 10500.0
    assert risk_manager.peak_equity == 11000.0

def test_record_pnl(risk_manager):
    risk_manager.record_pnl(100.0)
    assert risk_manager.daily.realised_pnl == 100.0
    assert risk_manager.daily.trade_count == 1

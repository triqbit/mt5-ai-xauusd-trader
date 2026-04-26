
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_positions = 3
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    return cfg

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(config=mock_config, account_balance=10000.0)

def test_update_equity(risk_manager):
    risk_manager.update_equity(10500.0)
    assert risk_manager.balance == 10500.0
    assert risk_manager.peak_equity == 10500.0
    assert risk_manager.daily.peak_equity == 10500.0

    risk_manager.update_equity(10200.0)
    assert risk_manager.balance == 10200.0
    assert risk_manager.peak_equity == 10500.0
    assert risk_manager.daily.peak_equity == 10500.0

def test_circuit_breaker(risk_manager):
    # Initial balance 10000, peak 10000.
    # Set equity to 8400 (16% drawdown)
    risk_manager.update_equity(8400.0)
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

def test_daily_loss(risk_manager, mock_config):
    risk_manager.record_pnl(-600.0) # 6% loss on 10000 peak
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

def test_max_positions(risk_manager, mock_config):
    risk_manager.open_positions = {"EURUSD": 123, "GBPUSD": 456, "USDJPY": 789}
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

def test_symbol_allocation(risk_manager):
    signal = TradeSignal(
        symbol="BTCUSD", # Not in ALLOCATION_WEIGHTS
        direction=1,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is False

def test_minimum_confidence(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.5 # Threshold is 0.55
    )
    assert risk_manager.approve(signal) is False

def test_risk_reward(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0, # risk 10
        take_profit=2010.0, # reward 10, R:R = 1.0 (threshold 1.5)
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is False

def test_kelly_sizing(risk_manager, mock_config):
    # win_rate=0.6, avg_win=20, avg_loss=10
    # Kelly = (0.6*20 - 0.4*10)/20 = (12 - 4)/20 = 8/20 = 0.4
    # Capped at 0.25
    # risk_capital = 10000 * 0.01 = 100
    # lot_size = (100 * 0.25) / (10 * 1.0) = 25 / 10 = 2.5
    lots = risk_manager.size_position("XAUUSD", 0.6, 20.0, 10.0)
    assert lots == 2.5

def test_approve_pass(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1980.0, # risk 20
        take_profit=2040.0, # reward 40, R:R = 2.0
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is True

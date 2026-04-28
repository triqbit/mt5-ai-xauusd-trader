import pytest
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig

@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="test",
        mt5_server="test",
        max_daily_trades=10,
        max_consecutive_losses=2,
        risk_per_trade=0.01  # Explicitly set to a safe value
    )

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

def test_ensemble_dissent_rejection(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        model_votes={"ppo": 1, "lstm": -1}  # Direct opposition
    )
    assert risk_manager.approve(signal) is False

def test_ensemble_no_dissent_approval(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        model_votes={"ppo": 1, "lstm": 0}  # No opposition
    )
    assert risk_manager.approve(signal) is True

def test_daily_trade_limit(risk_manager):
    risk_manager.daily.trade_count = 10
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        model_votes={"ppo": 1}
    )
    assert risk_manager.approve(signal) is False

def test_consecutive_losses_halt(risk_manager):
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-50.0)
    assert risk_manager.daily.consecutive_losses == 2

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        model_votes={"ppo": 1}
    )
    assert risk_manager.approve(signal) is False

def test_consecutive_losses_reset_on_win(risk_manager):
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(50.0)
    assert risk_manager.daily.consecutive_losses == 0

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        model_votes={"ppo": 1}
    )
    assert risk_manager.approve(signal) is True

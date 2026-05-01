
import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.risk_per_trade = 0.01
    return cfg

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(mock_config, account_balance=10000.0)

def test_consecutive_losses_halting(risk_manager):
    # Simulate 3 consecutive losses
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-50.0)
    risk_manager.record_pnl(-25.0)

    assert risk_manager.daily.consecutive_losses == 3

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        algo_votes={"ppo": 1, "lstm": 1, "dreamer": 1}
    )

    assert risk_manager.approve(signal) is False
    # Rejection reason would be "Too many consecutive losses"

def test_consecutive_losses_reset_on_win(risk_manager):
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-50.0)
    assert risk_manager.daily.consecutive_losses == 2

    risk_manager.record_pnl(10.0) # Win
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
        algo_votes={"ppo": 1, "lstm": 1, "dreamer": 1}
    )
    assert risk_manager.approve(signal) is True

def test_ensemble_consensus_majority(risk_manager):
    # 2/3 agree - Should Pass
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        algo_votes={"ppo": 1, "lstm": 1, "dreamer": 0}
    )
    assert risk_manager.approve(signal) is True

def test_ensemble_consensus_fail_no_majority(risk_manager):
    # 1/3 agree - Should Fail
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        algo_votes={"ppo": 1, "lstm": 0, "dreamer": 0}
    )
    assert risk_manager.approve(signal) is False

def test_ensemble_consensus_fail_strong_dissent(risk_manager):
    # 2/3 agree but 1 strongly dissents - Should Fail
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        algo_votes={"ppo": 1, "lstm": 1, "dreamer": -1}
    )
    assert risk_manager.approve(signal) is False

import pytest
from unittest.mock import MagicMock
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.max_daily_trades = 10
    cfg.max_consecutive_losses = 3
    cfg.circuit_breaker_threshold = 0.15
    cfg.confidence_threshold = 0.6
    cfg.min_risk_reward = 1.5
    cfg.ensemble_dissent_allowed = False
    return cfg

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(mock_config, account_balance=10000.0)

def test_ensemble_consensus_pass(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": 1}
    )
    assert risk_manager._check_ensemble_consensus(signal) is True

def test_ensemble_consensus_dissent_blocked(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": -1} # Dissent
    )
    assert risk_manager._check_ensemble_consensus(signal) is False

def test_ensemble_consensus_dissent_allowed(risk_manager):
    risk_manager.cfg.ensemble_dissent_allowed = True
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": -1} # Dissent
    )
    assert risk_manager._check_ensemble_consensus(signal) is True

def test_consecutive_losses_blocking(risk_manager):
    risk_manager.cfg.max_consecutive_losses = 3

    risk_manager.record_pnl(-100.0)
    assert risk_manager._check_consecutive_losses() is True

    risk_manager.record_pnl(-50.0)
    assert risk_manager._check_consecutive_losses() is True

    risk_manager.record_pnl(-20.0)
    # Now at 3 consecutive losses
    assert risk_manager._check_consecutive_losses() is False

def test_consecutive_losses_reset_on_win(risk_manager):
    risk_manager.cfg.max_consecutive_losses = 3

    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-50.0)
    risk_manager.record_pnl(10.0) # Win

    assert risk_manager.consecutive_losses == 0
    assert risk_manager._check_consecutive_losses() is True

def test_daily_trade_cap_including_open_positions(risk_manager):
    risk_manager.cfg.max_daily_trades = 3

    # 1 closed trade
    risk_manager.record_pnl(10.0)
    assert risk_manager._check_daily_trade_cap() is True

    # 1 open trade
    risk_manager.open_positions["XAUUSD"] = 12345
    assert risk_manager._check_daily_trade_cap() is True

    # 1 more open trade (total 3)
    risk_manager.open_positions["EURUSD"] = 67890
    assert risk_manager._check_daily_trade_cap() is False

def test_approve_cascade_failure_consensus(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": -1} # Dissent
    )
    # All other checks should pass, but consensus fails
    assert risk_manager.approve(signal) is False

def test_approve_cascade_failure_consecutive_losses(risk_manager):
    risk_manager.cfg.max_consecutive_losses = 2
    risk_manager.record_pnl(-10.0)
    risk_manager.record_pnl(-10.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": 1}
    )
    assert risk_manager.approve(signal) is False

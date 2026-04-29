
import pytest
from unittest.mock import MagicMock
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig

@pytest.fixture
def mock_config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_consecutive_losses = 3
    cfg.max_daily_trades = 5
    cfg.ensemble_dissent_allowed = False
    cfg.max_positions = 10
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    return cfg

@pytest.fixture
def risk_manager(mock_config):
    return RiskManager(config=mock_config, account_balance=10000.0)

@pytest.fixture
def base_signal():
    return TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        votes={"ppo": 1, "lstm": 1}
    )

def test_consecutive_losses_guard(risk_manager, base_signal):
    # Initial state: 0 losses, should approve
    assert risk_manager.approve(base_signal) is True

    # Simulate 3 losses
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-100.0)

    # Should reject now
    assert risk_manager.approve(base_signal) is False

    # Simulate a win
    risk_manager.record_pnl(200.0)

    # Should approve again
    assert risk_manager.approve(base_signal) is True

def test_max_daily_trades_guard(risk_manager, base_signal):
    # Initial state: 0 trades
    assert risk_manager.approve(base_signal) is True

    # Simulate 5 trades
    for _ in range(5):
        risk_manager.record_pnl(10.0)

    # Should reject now
    assert risk_manager.approve(base_signal) is False

def test_ensemble_dissent_guard(risk_manager, base_signal):
    # Consistent votes: should approve
    base_signal.votes = {"ppo": 1, "lstm": 1}
    assert risk_manager.approve(base_signal) is True

    # Dissenting votes (BUY and SELL): should reject
    base_signal.votes = {"ppo": 1, "lstm": -1}
    assert risk_manager.approve(base_signal) is False

    # HOLD and BUY: should approve (no direct opposition)
    base_signal.votes = {"ppo": 1, "lstm": 0}
    assert risk_manager.approve(base_signal) is True

def test_ensemble_dissent_allowed(risk_manager, base_signal):
    risk_manager.cfg.ensemble_dissent_allowed = True
    base_signal.votes = {"ppo": 1, "lstm": -1}
    # Should approve because dissent is allowed
    assert risk_manager.approve(base_signal) is True


import pytest
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats
from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from unittest.mock import MagicMock

@pytest.fixture
def config():
    cfg = MagicMock(spec=TradingConfig)
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    cfg.risk_per_trade = 0.01
    cfg.consecutive_loss_limit = 3
    cfg.unsafe_regimes = ["news_shock", "unknown"]
    return cfg

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

def test_ensemble_consensus_buy_no_dissent(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        per_algo_votes={"ppo": 0, "lstm": 0}  # 0=BUY legacy
    )
    assert risk_manager._check_ensemble_consensus(signal) is True

def test_ensemble_consensus_buy_with_dissent(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        per_algo_votes={"ppo": 0, "lstm": 1}  # 1=SELL legacy
    )
    assert risk_manager._check_ensemble_consensus(signal) is False

def test_ensemble_consensus_sell_with_dissent(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.SELL,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1980.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        per_algo_votes={"ppo": 0, "lstm": 1}  # 0=BUY legacy
    )
    assert risk_manager._check_ensemble_consensus(signal) is False

def test_regime_safety(risk_manager):
    assert risk_manager._check_regime_safety("trending") is True
    assert risk_manager._check_regime_safety("ranging") is True
    assert risk_manager._check_regime_safety("news_shock") is False
    assert risk_manager._check_regime_safety("unknown") is False

def test_consecutive_losses_circuit_breaker(risk_manager):
    risk_manager.daily.consecutive_losses = 2
    assert risk_manager._check_consecutive_losses() is True

    risk_manager.daily.consecutive_losses = 3
    assert risk_manager._check_consecutive_losses() is False

def test_record_pnl_updates_consecutive_losses(risk_manager):
    assert risk_manager.daily.consecutive_losses == 0

    risk_manager.record_pnl(-100.0)
    assert risk_manager.daily.consecutive_losses == 1

    risk_manager.record_pnl(-50.0)
    assert risk_manager.daily.consecutive_losses == 2

    risk_manager.record_pnl(10.0)
    assert risk_manager.daily.consecutive_losses == 0

def test_approve_cascade_integration(risk_manager):
    # Valid signal
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.7,
        per_algo_votes={"ppo": 0},
        market_regime="trending"
    )
    assert risk_manager.approve(signal) is True

    # Rejection by regime
    signal.market_regime = "news_shock"
    assert risk_manager.approve(signal) is False

    # Rejection by dissent
    signal.market_regime = "trending"
    signal.per_algo_votes = {"ppo": 1} # SELL vote
    assert risk_manager.approve(signal) is False

    # Rejection by consecutive losses
    signal.per_algo_votes = {"ppo": 0}
    risk_manager.daily.consecutive_losses = 3
    assert risk_manager.approve(signal) is False

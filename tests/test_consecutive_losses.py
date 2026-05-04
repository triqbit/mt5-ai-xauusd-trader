"""
Tests for RiskManager's consecutive loss limit logic.
"""
import pytest
from src.core.config import TradingConfig
from src.trading.risk_manager import RiskManager, TradeSignal, DailyStats

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    monkeypatch.setenv("CONSECUTIVE_LOSS_LIMIT", "3")
    return TradingConfig()

@pytest.fixture
def risk_manager(config):
    return RiskManager(config, account_balance=10000.0)

def test_consecutive_loss_limit(risk_manager):
    """Test that RiskManager correctly tracks and enforces consecutive losses."""
    # 1. Initially should pass
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.8
    )
    assert risk_manager.approve(signal) is True

    # 2. Record 2 losses
    risk_manager.record_pnl(-100.0)
    risk_manager.record_pnl(-150.0)
    assert risk_manager.daily.consecutive_losses == 2
    assert risk_manager.approve(signal) is True

    # 3. Record 3rd loss
    risk_manager.record_pnl(-50.0)
    assert risk_manager.daily.consecutive_losses == 3

    # 4. Should now be rejected
    assert risk_manager.approve(signal) is False

    # 5. Record a win, should reset and pass
    risk_manager.record_pnl(200.0)
    assert risk_manager.daily.consecutive_losses == 0
    assert risk_manager.approve(signal) is True

def test_circuit_breaker_config(risk_manager, monkeypatch):
    """Test that circuit breaker threshold is read from config."""
    # Default is 0.15 (15%)
    risk_manager.peak_equity = 10000.0
    risk_manager.balance = 8400.0  # 16% drawdown

    signal = TradeSignal("XAUUSD", 1, 2000.0, 1990.0, 2020.0, 0.1, "test", 0.8)
    assert risk_manager.approve(signal) is False

    # Set higher threshold in config
    risk_manager.cfg.circuit_breaker_threshold = 0.20
    assert risk_manager.approve(signal) is True

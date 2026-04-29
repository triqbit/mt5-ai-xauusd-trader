"""Tests for src.trading.risk_engine module."""
import pytest
from src.trading.risk_engine import RiskEngine
from src.core.config import TradingConfig

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "test")
    monkeypatch.setenv("MT5_SERVER", "test")
    return TradingConfig(
        risk_per_trade=0.01,
        max_trades_per_day=5,
        max_losing_streak=3,
        confidence_threshold=0.6
    )

@pytest.fixture
def risk_engine(config):
    return RiskEngine(config)

def test_calculate_lot_size(risk_engine):
    """Test ATR-based lot size calculation."""
    # Equity=10000, Risk=1% (100), ATR=2.0, TickVal=10, TickSize=0.01
    # lot_size = 100 / (2.0 * (10 / 0.01)) = 100 / (2.0 * 1000) = 100 / 2000 = 0.05
    lot_size = risk_engine.calculate_lot_size(
        equity=10000.0,
        atr=2.0,
        tick_value=10.0,
        tick_size=0.01
    )
    assert lot_size == 0.05

def test_validate_execution_drawdown(risk_engine):
    """Test drawdown circuit breaker."""
    account_info = {"equity": 7000.0, "balance": 7000.0, "margin_level": 500.0}
    risk_engine.peak_equity = 10000.0  # 30% drawdown
    assert risk_engine.validate_execution(account_info, 0.7) is False

def test_validate_execution_daily_loss(risk_engine):
    """Test daily loss circuit breaker."""
    account_info = {"equity": 10000.0, "balance": 10000.0, "margin_level": 500.0}
    risk_engine.peak_equity = 10000.0
    risk_engine.daily_realized_pnl = -550.0  # 5.5% loss
    assert risk_engine.validate_execution(account_info, 0.7) is False

def test_validate_execution_trade_limit(risk_engine):
    """Test daily trade count limit."""
    account_info = {"equity": 10000.0, "balance": 10000.0, "margin_level": 500.0}
    risk_engine.trades_today = 5
    assert risk_engine.validate_execution(account_info, 0.7) is False

def test_validate_execution_confidence(risk_engine):
    """Test confidence threshold."""
    account_info = {"equity": 10000.0, "balance": 10000.0, "margin_level": 500.0}
    assert risk_engine.validate_execution(account_info, 0.5) is False

def test_validate_execution_losing_streak(risk_engine):
    """Test losing streak limit."""
    account_info = {"equity": 10000.0, "balance": 10000.0, "margin_level": 500.0}
    risk_engine.consecutive_losses = 3
    assert risk_engine.validate_execution(account_info, 0.7) is False

def test_update_stats(risk_engine):
    """Test stat tracking."""
    risk_engine.update_stats(-100.0)
    assert risk_engine.daily_realized_pnl == -100.0
    assert risk_engine.trades_today == 1
    assert risk_engine.consecutive_losses == 1

    risk_engine.update_stats(200.0)
    assert risk_engine.daily_realized_pnl == 100.0
    assert risk_engine.trades_today == 2
    assert risk_engine.consecutive_losses == 0

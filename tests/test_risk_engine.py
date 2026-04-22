"""Tests for src.trading.risk_engine module."""
import pytest
from datetime import date
from src.trading.risk_engine import RiskEngine, DailyStats
from src.core.config import TradingConfig
from src.trading.risk_manager import TradeSignal

@pytest.fixture
def config():
    return TradingConfig(
        MT5_LOGIN=123,
        MT5_PASSWORD="pass",
        MT5_SERVER="server",
        risk_per_trade=0.01,
        max_daily_loss_limit=0.05,
        max_equity_drawdown=0.30,
        confidence_threshold=0.55
    )

@pytest.fixture
def risk_engine(config):
    return RiskEngine(config, account_balance=10000.0)

def test_calculate_lot_size_normal(risk_engine):
    """Test lot sizing calculation under normal conditions."""
    # Equity=10000, Risk=1% -> 100 USD risk
    # Price=2000, SL=1990 -> 10 USD distance
    # Lot = 100 / (10 * 100) = 0.10
    lot = risk_engine.calculate_lot_size(entry_price=2000.0, stop_loss=1990.0, atr=5.0)
    assert lot == 0.10

def test_calculate_lot_size_orange_alert(risk_engine):
    """Test lot sizing reduction during Orange Alert (>3% daily loss)."""
    risk_engine.daily.realised_pnl = -350.0  # 3.5% loss
    lot = risk_engine.calculate_lot_size(entry_price=2000.0, stop_loss=1990.0, atr=5.0)
    # Risk 1% -> 0.5% due to orange alert -> 50 USD risk
    # Lot = 50 / (10 * 100) = 0.05
    assert lot == 0.05

def test_validate_signal_pass(risk_engine):
    """Test signal validation passes under normal conditions."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.10,
        algorithm="test",
        confidence=0.70
    )
    assert risk_engine.validate_signal(signal) is True

def test_validate_signal_circuit_breaker(risk_engine):
    """Test circuit breaker triggers on drawdown."""
    risk_engine.balance = 6000.0  # 40% drawdown from 10000.0
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.10,
        algorithm="test",
        confidence=0.70
    )
    assert risk_engine.validate_signal(signal) is False
    assert risk_engine.is_halted is True

def test_validate_signal_low_confidence(risk_engine):
    """Test rejection on low confidence."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.10,
        algorithm="test",
        confidence=0.40
    )
    assert risk_engine.validate_signal(signal) is False

def test_update_performance(risk_engine):
    """Test performance tracking updates stats correctly."""
    risk_engine.update_performance(-100.0)
    assert risk_engine.daily.realised_pnl == -100.0
    assert risk_engine.daily.trade_count == 1
    assert risk_engine.balance == 9900.0
    assert risk_engine.daily.consecutive_losses == 1

    risk_engine.update_performance(200.0)
    assert risk_engine.daily.realised_pnl == 100.0
    assert risk_engine.daily.consecutive_losses == 0
    assert risk_engine.balance == 10100.0
    assert risk_engine.peak_equity == 10100.0

"""Tests for RiskEngine module."""
import pytest
from unittest.mock import MagicMock
from src.trading.risk_engine import RiskEngine
from src.trading.risk_manager import TradeSignal
from src.core.config import TradingConfig

@pytest.fixture
def config():
    return TradingConfig(
        mt5_password="test",
        mt5_server="test",
        risk_per_trade=0.01,
        daily_loss_limit=0.05,
        max_drawdown_limit=0.30
    )

def test_risk_engine_initialization(config):
    re = RiskEngine(config, account_balance=10000.0)
    assert re.balance == 10000.0
    assert re.peak_equity == 10000.0

def test_risk_engine_approve_happy_path(config):
    re = RiskEngine(config, account_balance=10000.0)
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    assert re.approve(signal) is True

def test_risk_engine_circuit_breaker(config):
    re = RiskEngine(config, account_balance=10000.0)
    re.update_equity(6000.0) # 40% drawdown
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    assert re.approve(signal) is False

def test_position_sizing(config):
    re = RiskEngine(config, account_balance=10000.0)
    # Risk 1% of 10000 = 100.
    # Entry 2300, SL 2290 -> Risk per unit = 10.
    # 100 / (10 * 100) = 0.1 lots
    # But limited by 10% equity with 10:1 leverage:
    # (10000 * 0.1) / (2300 * 100 / 10) = 1000 / 23000 = 0.043... -> 0.04
    size = re.calculate_position_size("XAUUSD", 2300.0, 2290.0, 5.0)
    assert size == 0.04


import pytest
from datetime import datetime, UTC
from pydantic import ValidationError
from src.trading.risk_manager import TradeSignal, RiskManager
from src.core.config import TradingConfig
import os

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("MT5_LOGIN", "12345")
    monkeypatch.setenv("MT5_PASSWORD", "test_password")
    monkeypatch.setenv("MT5_SERVER", "test_server")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

def test_trade_signal_valid_instantiation():
    """Verify that a valid signal can be instantiated."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2250.0,
        take_profit=2400.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == 1
    assert signal.entry_price == 2300.0
    assert signal.lot_size == 0.1
    assert isinstance(signal.timestamp, datetime)

@pytest.mark.parametrize("field, value", [
    ("direction", 2),
    ("direction", -2),
    ("entry_price", -1.0),
    ("entry_price", 0.0),
    ("stop_loss", -50.0),
    ("take_profit", 0.0),
    ("lot_size", 0.005),
    ("confidence", -0.1),
    ("confidence", 1.1),
])
def test_trade_signal_invalid_values(field, value):
    """Verify that invalid values raise ValidationError."""
    data = {
        "symbol": "XAUUSD",
        "direction": 1,
        "entry_price": 2300.0,
        "stop_loss": 2250.0,
        "take_profit": 2400.0,
        "lot_size": 0.1,
        "algorithm": "ensemble",
        "confidence": 0.85
    }
    data[field] = value
    with pytest.raises(ValidationError):
        TradeSignal(**data)

def test_risk_manager_approval_with_valid_signal():
    """Verify RiskManager approve logic with a valid signal."""
    config = TradingConfig()
    risk_mgr = RiskManager(config, account_balance=10000.0)

    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2250.0,
        take_profit=2400.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )

    # Should pass basic filters (XAUUSD is in approved portfolio)
    assert risk_mgr.approve(signal) is True

def test_risk_manager_rejection_low_confidence():
    """Verify RiskManager rejects low confidence signals."""
    config = TradingConfig()
    risk_mgr = RiskManager(config, account_balance=10000.0)

    # Confidence 0.51 is below default 0.55 threshold in RiskManager
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2300.0,
        stop_loss=2250.0,
        take_profit=2400.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.51
    )

    assert risk_mgr.approve(signal) is False

def test_risk_manager_rejection_unapproved_symbol():
    """Verify RiskManager rejects symbols not in ALLOCATION_WEIGHTS."""
    config = TradingConfig()
    risk_mgr = RiskManager(config, account_balance=10000.0)

    signal = TradeSignal(
        symbol="INVALID",
        direction=1,
        entry_price=1.0,
        stop_loss=0.5,
        take_profit=2.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.9
    )

    assert risk_mgr.approve(signal) is False

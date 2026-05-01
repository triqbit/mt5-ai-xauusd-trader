
import pytest
from datetime import datetime
from src.trading.risk_manager import RiskManager, TradeSignal, TradingConfig

@pytest.fixture
def risk_manager():
    # Mock TradingConfig to avoid validation errors
    cfg = TradingConfig(
        mt5_login=12345,
        mt5_password="password",
        mt5_server="MetaQuotes-Demo"
    )
    cfg.risk_per_trade = 0.01
    cfg.max_daily_loss = 0.05
    cfg.max_positions = 3
    return RiskManager(cfg, account_balance=10000.0)

def test_get_rejection_reason_all_pass(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    reasons = risk_manager._get_rejection_reason(signal)
    assert len(reasons) == 0

def test_get_rejection_reason_low_confidence(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.4
    )
    reasons = risk_manager._get_rejection_reason(signal)
    assert len(reasons) == 1
    assert "Confidence" in reasons[0]

def test_get_rejection_reason_bad_rr(risk_manager):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2005.0, # 1:0.5 RR
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    reasons = risk_manager._get_rejection_reason(signal)
    assert len(reasons) == 1
    assert "Risk-Reward ratio" in reasons[0]

def test_approve_calls_rejection_reason(risk_manager, mocker):
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=1,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    spy = mocker.spy(risk_manager, "_get_rejection_reason")
    approved = risk_manager.approve(signal)
    assert approved is True
    spy.assert_called_once_with(signal)



import pytest

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
    cfg.confidence_threshold = 0.55
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
    assert any("Confidence" in r for r in reasons)

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
    assert any("Risk-Reward ratio" in r for r in reasons)

def test_get_rejection_reason_circuit_breaker(risk_manager):
    risk_manager.update_equity(10000.0)
    risk_manager.update_equity(8400.0) # 16% DD
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
    assert any("Circuit breaker" in r for r in reasons)

def test_get_rejection_reason_daily_loss(risk_manager):
    risk_manager.record_pnl(-600.0) # 6% loss
    risk_manager.update_equity(9400.0)
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
    assert any("Daily loss limit" in r for r in reasons)

def test_get_rejection_reason_max_positions(risk_manager):
    risk_manager.open_positions = {"EURUSD": 1, "GBPUSD": 2, "USDJPY": 3}
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
    assert any("Max positions reached" in r for r in reasons)

def test_get_rejection_reason_invalid_symbol(risk_manager):
    signal = TradeSignal(
        symbol="INVALID",
        direction=1,
        entry_price=1.0,
        stop_loss=0.9,
        take_profit=1.2,
        lot_size=0.1,
        algorithm="test",
        confidence=0.7
    )
    reasons = risk_manager._get_rejection_reason(signal)
    assert any("not in approved portfolio" in r for r in reasons)

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

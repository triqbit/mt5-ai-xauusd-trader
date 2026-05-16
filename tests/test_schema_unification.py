import pytest
from src.core.schemas import RiskDecision, ExecutionDecision, TradeSignal, SignalDirection
from pydantic import ValidationError

def test_risk_decision_bool():
    approved = RiskDecision(is_approved=True, reason="Approved", adjusted_lot_size=0.1)
    rejected = RiskDecision(is_approved=False, reason="Rejected")

    assert bool(approved) is True
    assert bool(rejected) is False

def test_execution_decision_bool():
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )
    approved = ExecutionDecision(
        signal=signal,
        is_approved=True,
        confidence_score=0.8,
        blocked_by=None,
        trace={}
    )
    rejected = ExecutionDecision(
        signal=signal,
        is_approved=False,
        confidence_score=0.8,
        blocked_by="TEST",
        trace={}
    )

    assert bool(approved) is True
    assert bool(rejected) is False

def test_execution_decision_validation():
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Should fail if is_approved=False but no blocked_by
    with pytest.raises(ValidationError):
        ExecutionDecision(
            signal=signal,
            is_approved=False,
            confidence_score=0.8,
            blocked_by=None,
            trace={}
        )

    # Should fail if is_approved=True but blocked_by is set
    with pytest.raises(ValidationError):
        ExecutionDecision(
            signal=signal,
            is_approved=True,
            confidence_score=0.8,
            blocked_by="REASON",
            trace={}
        )

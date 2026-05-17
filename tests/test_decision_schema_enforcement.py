"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_decision_schema_enforcement.py

Verification tests for the unified decision schemas (RiskDecision, ExecutionDecision).
Ensures that runtime validation strictly prevents inconsistent decision states.
"""

import pytest
from pydantic import ValidationError

from src.core.schemas import ExecutionDecision, RiskDecision, TradeSignal
from src.core.constants import SignalDirection


def test_risk_decision_valid_approval():
    """Verify a valid approved risk decision can be instantiated."""
    decision = RiskDecision(
        is_approved=True,
        reason="Passed all layers",
        adjusted_lot_size=0.1,
        trace={"circuit_breaker": True}
    )
    assert decision.is_approved is True
    assert decision.reason == "Passed all layers"
    assert decision.adjusted_lot_size == 0.1


def test_risk_decision_valid_rejection():
    """Verify a valid rejected risk decision can be instantiated."""
    decision = RiskDecision(
        is_approved=False,
        reason="Daily loss limit hit",
        adjusted_lot_size=0.0,
        trace={"daily_loss": False}
    )
    assert decision.is_approved is False
    assert decision.reason == "Daily loss limit hit"
    assert decision.adjusted_lot_size == 0.0


def test_risk_decision_rejection_missing_reason():
    """Rejecting without a reason should fail validation."""
    with pytest.raises(ValidationError, match="A rejected risk decision must provide a 'reason'"):
        RiskDecision(
            is_approved=False,
            reason="",
            adjusted_lot_size=0.0
        )


def test_risk_decision_rejection_with_lot_size():
    """Rejecting while keeping a lot size > 0 should fail validation."""
    with pytest.raises(ValidationError, match="A rejected risk decision cannot have an adjusted lot size > 0"):
        RiskDecision(
            is_approved=False,
            reason="Risk too high",
            adjusted_lot_size=0.01
        )


def test_execution_decision_consistency(sample_trade_signal):
    """Verify consistency between is_approved and blocked_by in ExecutionDecision."""
    # Valid Approved
    ExecutionDecision(
        signal=sample_trade_signal,
        is_approved=True,
        confidence_score=0.8,
        blocked_by=None
    )

    # Valid Blocked
    ExecutionDecision(
        signal=sample_trade_signal,
        is_approved=False,
        confidence_score=0.8,
        blocked_by="ATR_VOLATILITY"
    )

    # Invalid: Approved but has blocked_by
    with pytest.raises(ValidationError, match="An approved decision cannot have a 'blocked_by' reason"):
        ExecutionDecision(
            signal=sample_trade_signal,
            is_approved=True,
            confidence_score=0.8,
            blocked_by="ERROR"
        )

    # Invalid: Blocked but no blocked_by
    with pytest.raises(ValidationError, match="A blocked decision must provide a 'blocked_by' reason"):
        ExecutionDecision(
            signal=sample_trade_signal,
            is_approved=False,
            confidence_score=0.8,
            blocked_by=None
        )


@pytest.fixture
def sample_trade_signal():
    """Provide a valid TradeSignal for testing."""
    return TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.75
    )

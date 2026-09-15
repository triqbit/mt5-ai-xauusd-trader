"""
Tests for centralized Pydantic schema enforcement and decision funnel validation.
"""

import pytest
from datetime import datetime, UTC
from pydantic import ValidationError
from src.core.schemas import ModelSignal, TradeSignal, RiskDecision, ExecutionDecision
from src.core.constants import SignalDirection

def test_model_signal_validation():
    """Verify ModelSignal enforces types and ranges."""
    # Valid signal
    sig = ModelSignal(direction=SignalDirection.BUY, confidence=0.85, metadata={"test": True})
    assert sig.direction == SignalDirection.BUY
    assert sig.confidence == 0.85

    # Invalid confidence (high)
    with pytest.raises(ValidationError):
        ModelSignal(direction=SignalDirection.BUY, confidence=1.1)

    # Invalid confidence (low)
    with pytest.raises(ValidationError):
        ModelSignal(direction=SignalDirection.BUY, confidence=-0.1)

def test_risk_decision_consistency():
    """Verify RiskDecision enforces rejection reasons."""
    # Valid approval
    dec = RiskDecision(is_approved=True, reason="Approved", adjusted_lot_size=0.1)
    assert dec.is_approved is True

    # Valid rejection
    dec = RiskDecision(is_approved=False, reason="Daily loss limit")
    assert dec.is_approved is False
    assert dec.reason == "Daily loss limit"

    # Invalid rejection (missing reason)
    with pytest.raises(ValidationError, match="A rejected risk decision must provide a 'reason'"):
        RiskDecision(is_approved=False)

def test_trade_signal_price_sanity():
    """Verify TradeSignal enforces price boundaries and R:R ratio."""
    base_params = {
        "symbol": "XAUUSD",
        "lot_size": 0.1,
        "algorithm": "test",
        "confidence": 0.8,
        "timestamp": datetime.now(UTC)
    }

    # Valid BUY
    TradeSignal(
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        **base_params
    )

    # Invalid BUY (SL above entry)
    with pytest.raises(ValidationError, match="BUY Stop Loss .* must be below Entry Price"):
        TradeSignal(
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=2010.0,
            take_profit=2030.0,
            **base_params
        )

    # Invalid R:R (below 1.5)
    with pytest.raises(ValidationError, match="Risk-Reward ratio .* is below the required minimum of 1.5"):
        TradeSignal(
            direction=SignalDirection.BUY,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2010.0,  # RR = 1.0
            **base_params
        )

def test_execution_decision_consistency():
    """Verify ExecutionDecision enforces rejection reasons."""
    trade_sig = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2020.0,
        lot_size=0.1,
        algorithm="test",
        confidence=0.8
    )

    # Valid approval
    ExecutionDecision(
        signal=trade_sig,
        is_approved=True,
        confidence_score=0.8
    )

    # Invalid approval (has blocked_by)
    with pytest.raises(ValidationError, match="An approved decision cannot have a 'blocked_by' reason"):
        ExecutionDecision(
            signal=trade_sig,
            is_approved=True,
            confidence_score=0.8,
            blocked_by="SpreadFilter"
        )

    # Invalid rejection (missing blocked_by)
    with pytest.raises(ValidationError, match="A blocked decision must provide a 'blocked_by' reason"):
        ExecutionDecision(
            signal=trade_sig,
            is_approved=False,
            confidence_score=0.8
        )

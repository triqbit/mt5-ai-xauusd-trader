"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_schemas_governance.py

Tests for Pydantic schema validation and governance.
"""


import pytest
from pydantic import ValidationError

from src.core.config import TradingConfig
from src.core.constants import SignalDirection
from src.core.schemas import ExecutionDecision, TradeSignal


def test_trade_signal_valid():
    """Verify valid TradeSignal instantiation."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    assert signal.symbol == "XAUUSD"
    assert signal.direction == SignalDirection.BUY

def test_trade_signal_invalid_symbol():
    """Verify SYMBOL_PATTERN enforcement."""
    with pytest.raises(ValidationError) as exc:
        TradeSignal(
            symbol="xauusd",  # Must be uppercase
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.85
        )
    assert "pattern" in str(exc.value).lower()

def test_trade_signal_invalid_rr_ratio():
    """Verify Risk-Reward ratio enforcement (minimum 1.5)."""
    with pytest.raises(ValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2310.0,  # RR = 10/10 = 1.0 (less than 1.5)
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.85
        )
    assert "risk-reward ratio" in str(exc.value).lower()

def test_trade_signal_frozen():
    """Verify TradeSignal is immutable."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )
    with pytest.raises(ValidationError) as exc:
        signal.symbol = "BTCUSD" # type: ignore
    assert "frozen" in str(exc.value).lower() or "immutable" in str(exc.value).lower()

def test_trade_signal_extra_forbid():
    """Verify TradeSignal forbids extra fields."""
    with pytest.raises(ValidationError) as exc:
        TradeSignal(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            entry_price=2300.0,
            stop_loss=2290.0,
            take_profit=2320.0,
            lot_size=0.1,
            algorithm="ensemble",
            confidence=0.85,
            extra_field="untrusted" # type: ignore
        )
    # Pydantic 2 error message changed slightly, but extra_forbidden is part of the type
    assert "extra inputs are not permitted" in str(exc.value).lower()

def test_execution_decision_blocking_invariant():
    """Verify that a blocked decision must have a reason."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2350.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )

    # Valid blocked decision
    decision = ExecutionDecision(
        signal=signal,
        is_approved=False,
        confidence_score=0.85,
        blocked_by="ATR_VOLATILITY",
        trace={"atr_volatility": {"passed": False, "ratio": 4.5}}
    )
    assert decision.blocked_by == "ATR_VOLATILITY"

    # Invalid: Not approved but blocked_by is None
    with pytest.raises(ValidationError) as exc:
        ExecutionDecision(
            signal=signal,
            is_approved=False,
            confidence_score=0.85,
            blocked_by=None,
            trace={}
        )
    assert "blocked decision must provide a 'blocked_by' reason" in str(exc.value).lower()

def test_execution_decision_approved_consistency():
    """Verify that an approved decision cannot have a blocked_by reason."""
    signal = TradeSignal(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=2300.0,
        stop_loss=2280.0,
        take_profit=2350.0,
        lot_size=0.1,
        algorithm="ensemble",
        confidence=0.85
    )

    with pytest.raises(ValidationError) as exc:
        ExecutionDecision(
            signal=signal,
            is_approved=True,
            confidence_score=0.85,
            blocked_by="SOME_FILTER",
            trace={}
        )
    assert "approved decision cannot have a 'blocked_by' reason" in str(exc.value).lower()

def test_trading_config_validation(monkeypatch):
    """Verify TradingConfig enforces SYMBOL_PATTERN and VALID_TIMEFRAMES."""
    # We use monkeypatch to avoid loading real .env
    monkeypatch.setenv("MT5_PASSWORD", "secret")
    monkeypatch.setenv("MT5_SERVER", "server")

    # Invalid symbol - using validation alias for Pydantic Settings
    with pytest.raises(ValidationError):
        TradingConfig(SYMBOL="gold")

    # Invalid timeframe
    with pytest.raises(ValidationError):
        TradingConfig(timeframe="S1")

    # Valid config
    cfg = TradingConfig(SYMBOL="XAUUSD", timeframe="H1")
    assert cfg.symbol == "XAUUSD"
    assert cfg.timeframe == "H1"

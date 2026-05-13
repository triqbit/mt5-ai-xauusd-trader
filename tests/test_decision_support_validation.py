"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_decision_support_validation.py

Tests for DecisionSupportSystem schemas and validation.
"""


import pytest
from pydantic import ValidationError

from src.core.constants import DecisionStatus, SignalDirection
from src.core.decision_support import DecisionPacket, PerformanceContext
from src.core.explainability import (
    ExecutionSummary,
    RegimeContext,
    RiskAssessment,
    SignalExplanation,
)
from src.data.event_models import RiskStatus
from src.models.regime_detector import MarketRegime, RegimeInfo


@pytest.fixture
def valid_performance():
    return PerformanceContext(
        sharpe_ratio=2.1,
        profit_factor=1.8,
        recovery_factor=2.5,
        win_rate=0.65,
        win_loss_ratio=1.2,
        max_drawdown=0.15,
        total_trades=100
    )

@pytest.fixture
def mock_explanation():
    # Minimally valid mock explanation for schema testing
    return SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.75,
        execution_summary=ExecutionSummary(passed=True, summary="OK"),
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(passed=True, risk_reward_ratio=2.0),
        regime_context=RegimeContext(regime_name="Trending"),
        human_readable_summary="OK",
        machine_attribution={}
    )

@pytest.fixture
def valid_regime():
    return RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.8,
        volatility_index=1.0,
        transition_score=0.1
    )

@pytest.fixture
def valid_macro_risk():
    return RiskStatus(is_blocked=False, risk_multiplier=1.0)

def test_performance_context_win_rate_bounds():
    """Verify win_rate is constrained between 0 and 1."""
    with pytest.raises(ValidationError):
        PerformanceContext(win_rate=1.1, total_trades=10)
    with pytest.raises(ValidationError):
        PerformanceContext(win_rate=-0.1, total_trades=10)

def test_performance_context_frozen():
    """Verify PerformanceContext is immutable."""
    perf = PerformanceContext(win_rate=0.5, total_trades=10)
    with pytest.raises(ValidationError):
        perf.win_rate = 0.6 # type: ignore

def test_decision_packet_executable_consistency(mock_explanation, valid_regime, valid_macro_risk, valid_performance):
    """Verify executable state invariants in DecisionPacket."""
    # Cannot be executable if BLOCKED
    with pytest.raises(ValidationError) as exc:
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.BLOCKED,
            decision_score=80.0,
            sizing_multiplier=1.0,
            is_executable=True,
            explanation=mock_explanation,
            regime=valid_regime,
            macro_risk=valid_macro_risk,
            performance=valid_performance
        )
    assert "decision cannot be executable with a blocked status level" in str(exc.value).lower()

    # Cannot be executable if blocking reasons exist
    with pytest.raises(ValidationError) as exc:
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.EXECUTE,
            decision_score=80.0,
            sizing_multiplier=1.0,
            is_executable=True,
            blocking_reasons=["Some reason"],
            explanation=mock_explanation,
            regime=valid_regime,
            macro_risk=valid_macro_risk,
            performance=valid_performance
        )
    assert "decision cannot be executable with active blocking reasons" in str(exc.value).lower()

def test_decision_packet_frozen(mock_explanation, valid_regime, valid_macro_risk, valid_performance):
    """Verify DecisionPacket is immutable."""
    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        consensus="Strong",
        status_level=DecisionStatus.EXECUTE,
        decision_score=80.0,
        sizing_multiplier=1.0,
        is_executable=True,
        explanation=mock_explanation,
        regime=valid_regime,
        macro_risk=valid_macro_risk,
        performance=valid_performance
    )
    with pytest.raises(ValidationError):
        packet.symbol = "BTCUSD" # type: ignore

def test_decision_packet_extra_forbid(mock_explanation, valid_regime, valid_macro_risk, valid_performance):
    """Verify extra fields are forbidden."""
    with pytest.raises(ValidationError):
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.EXECUTE,
            decision_score=80.0,
            sizing_multiplier=1.0,
            is_executable=True,
            explanation=mock_explanation,
            regime=valid_regime,
            macro_risk=valid_macro_risk,
            performance=valid_performance,
            untrusted_field="injection" # type: ignore
        )

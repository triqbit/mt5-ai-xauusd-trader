

from datetime import UTC, datetime
from typing import Any, cast

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
from src.data.event_intelligence import RiskStatus
from src.models.regime_detector import MarketRegime, RegimeInfo


@pytest.fixture
def valid_components() -> dict[str, object]:
    explanation = SignalExplanation(
        signal_id=None,
        timestamp=datetime.now(UTC),
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        execution_summary=ExecutionSummary(passed=True, filters=[], summary="All passed"),
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=True,
            rejection_reasons=[],
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.0,
            kelly_fraction=0.0,
            summary="Good",
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.9,
            volatility_state="Normal",
            is_favorable=True,
            summary="Stable",
        ),
        human_readable_summary="Test",
        machine_attribution={},
    )
    regime = RegimeInfo(
        label=MarketRegime.TRENDING, confidence=0.9, transition_score=0.1, volatility_index=1.0
    )
    macro_risk = RiskStatus(
        is_blocked=False,
        risk_multiplier=1.0,
        active_events=[],
        blocking_events=[],
        reason=None,
    )
    performance = PerformanceContext(
        sharpe_ratio=0.0,
        profit_factor=0.0,
        recovery_factor=0.0,
        win_rate=0.0,
        win_loss_ratio=0.0,
        max_drawdown=0.0,
        total_trades=10,
    )
    return {
        "explanation": explanation,
        "regime": regime,
        "macro_risk": macro_risk,
        "performance": performance,
    }


def test_decision_packet_valid_execute(valid_components: dict[str, Any]) -> None:
    """Verify that a valid executable packet passes validation."""
    packet = DecisionPacket(
        timestamp=datetime.now(UTC),
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        consensus="Strong",
        status_level=DecisionStatus.EXECUTE,
        decision_score=85.0,
        sizing_multiplier=1.0,
        is_executable=True,
        blocking_reasons=[],
        explanation=cast(SignalExplanation, valid_components["explanation"]),
        regime=cast(RegimeInfo, valid_components["regime"]),
        macro_risk=cast(RiskStatus, valid_components["macro_risk"]),
        performance=cast(PerformanceContext, valid_components["performance"]),
    )
    assert packet.is_executable is True
    assert not packet.blocking_reasons

def test_decision_packet_valid_blocked(valid_components):
    """Verify that a valid blocked packet passes validation."""
    packet = DecisionPacket(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        consensus="Weak",
        status_level=DecisionStatus.BLOCKED,
        decision_score=40.0,
        sizing_multiplier=0.0,
        is_executable=False,
        blocking_reasons=["Risk too high"],
        **valid_components
    )
    assert packet.is_executable is False
    assert "Risk too high" in packet.blocking_reasons

def test_decision_packet_invalid_executable_with_reasons(valid_components):
    """Verify that an executable packet cannot have blocking reasons."""
    with pytest.raises(ValidationError, match="cannot be executable with active blocking reasons"):
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.EXECUTE,
            decision_score=85.0,
            sizing_multiplier=1.0,
            is_executable=True,
            blocking_reasons=["Something is wrong"],
            **valid_components
        )

def test_decision_packet_invalid_executable_with_blocked_status(valid_components):
    """Verify that an executable packet cannot have BLOCKED status."""
    with pytest.raises(ValidationError, match="cannot be executable with a BLOCKED status level"):
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.BLOCKED,
            decision_score=85.0,
            sizing_multiplier=1.0,
            is_executable=True,
            blocking_reasons=[],
            **valid_components
        )

def test_decision_packet_invalid_non_executable_with_execute_status(valid_components):
    """Verify that a non-executable packet cannot have EXECUTE status."""
    with pytest.raises(ValidationError, match="Status level cannot be EXECUTE if is_executable is False"):
        DecisionPacket(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            consensus="Strong",
            status_level=DecisionStatus.EXECUTE,
            decision_score=85.0,
            sizing_multiplier=1.0,
            is_executable=False,
            blocking_reasons=["Macro block"],
            **valid_components
        )

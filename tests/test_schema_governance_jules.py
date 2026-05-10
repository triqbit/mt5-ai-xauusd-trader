import pytest
from pydantic import ValidationError
from src.core.explainability import FeatureContribution, ModelAttribution, RiskAssessment, RegimeContext, SignalExplanation, ExecutionSummary
from src.core.decision_support import PerformanceContext
from src.core.constants import SignalDirection
from datetime import datetime, UTC

def test_feature_contribution_governance():
    # Valid
    fc = FeatureContribution(
        cluster_name="Trend",
        contribution_score=0.5,
        impact_level="High",
        summary="Test"
    )
    assert fc.contribution_score == 0.5

    # Invalid range
    with pytest.raises(ValidationError):
        FeatureContribution(
            cluster_name="Trend",
            contribution_score=1.5,
            impact_level="High",
            summary="Test"
        )

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        FeatureContribution(
            cluster_name="Trend",
            contribution_score=0.5,
            impact_level="High",
            summary="Test",
            extra="forbidden"
        )

    # Immutable
    with pytest.raises((ValidationError, AttributeError)):
        fc.contribution_score = 0.6

def test_performance_context_governance():
    # Valid
    pc = PerformanceContext(
        sharpe_ratio=2.5,
        profit_factor=2.1,
        recovery_factor=3.5,
        win_rate=0.6,
        win_loss_ratio=1.5,
        max_drawdown=0.1,
        total_trades=100
    )
    assert pc.sharpe_ratio == 2.5

    # Invalid range: profit_factor < 0
    with pytest.raises(ValidationError):
        PerformanceContext(profit_factor=-1.0)

    # Invalid range: max_drawdown > 1.0
    with pytest.raises(ValidationError):
        PerformanceContext(max_drawdown=1.5)

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        PerformanceContext(extra_field="fail")

def test_model_attribution_governance():
    # Valid
    ma = ModelAttribution(
        model_name="PPO",
        vote=SignalDirection.BUY,
        confidence=0.8,
        weight=0.5,
        is_dominant=True
    )
    assert ma.confidence == 0.8

    # Invalid range: confidence > 1.0
    with pytest.raises(ValidationError):
        ModelAttribution(
            model_name="PPO",
            vote=SignalDirection.BUY,
            confidence=1.1,
            weight=0.5
        )

def test_signal_explanation_governance():
    # Minimum valid signal explanation
    se = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.7,
        execution_summary=ExecutionSummary(passed=True, summary="OK"),
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(passed=True),
        regime_context=RegimeContext(regime_name="Trending", confidence=0.8, volatility_state="Normal", is_favorable=True, summary="OK"),
        human_readable_summary="Test",
        machine_attribution={}
    )
    assert se.total_confidence == 0.7

    # Invalid range: total_confidence < 0
    with pytest.raises(ValidationError):
        SignalExplanation.model_validate({**se.model_dump(), "total_confidence": -0.1})

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        SignalExplanation(
            symbol="XAUUSD",
            direction=SignalDirection.BUY,
            total_confidence=0.7,
            execution_summary=ExecutionSummary(passed=True, summary="OK"),
            model_attributions=[],
            feature_contributions=[],
            risk_assessment=RiskAssessment(passed=True),
            regime_context=RegimeContext(regime_name="Trending", confidence=0.8, volatility_state="Normal", is_favorable=True, summary="OK"),
            human_readable_summary="Test",
            machine_attribution={},
            extra="fail"
        )

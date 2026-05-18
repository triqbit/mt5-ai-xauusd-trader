"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_decision_support_v2.py

Advanced tests for DecisionSupportSystem enhancements, including executive summaries,
review flags, and complex decision scenarios.
"""

from datetime import datetime, timezone

import pytest

from src.core.constants import SignalDirection
from src.core.decision_support import (
    DecisionStatus,
    DecisionSupportSystem,
)
from src.core.explainability import (
    ExecutionSummary,
    ModelAttribution,
    RegimeContext,
    RiskAssessment,
    SignalExplanation,
)
from src.data.event_intelligence import RiskStatus
from src.models.regime_detector import MarketRegime, RegimeInfo


@pytest.fixture
def dss():
    return DecisionSupportSystem()

@pytest.fixture
def base_explanation():
    # Use a real SignalExplanation object to avoid Mock AttributeErrors in complex rendering
    explanation = SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.8,
        timestamp=datetime.now(timezone.utc),
        execution_summary=ExecutionSummary(passed=True, summary="Passed all filters."),
        model_attributions=[
            ModelAttribution(model_name="PPO", vote=SignalDirection.BUY, confidence=0.8, weight=1.0)
        ],
        feature_contributions=[],
        risk_assessment=RiskAssessment(passed=True, risk_reward_ratio=2.5, summary="Good R:R"),
        regime_context=RegimeContext(regime_name="Trending", confidence=0.9, is_favorable=True),
        human_readable_summary="Signal shows momentum alignment.",
        machine_attribution={}
    )
    return explanation

@pytest.fixture
def base_regime():
    return RegimeInfo(
        label=MarketRegime.TRENDING,
        confidence=0.9,
        volatility_index=1.1,
        transition_score=0.05
    )

@pytest.fixture
def base_macro():
    return RiskStatus(is_blocked=False, risk_multiplier=1.0)

def test_executive_summary_generation(dss, base_explanation, base_regime, base_macro):
    """Verify that executive summaries are generated correctly for different states."""

    # 1. High-Confidence EXECUTE state
    packet = dss.assemble_packet("XAUUSD", base_explanation, base_regime, base_macro, {})
    assert packet.status_level == DecisionStatus.EXECUTE
    assert "maximum confluence" in packet.executive_summary.lower()
    # Score: (1.0*40) + (0.9*30) + (min(2.5/3, 1)*20 + 10) = 40+27+16.66+10 = 93.66 -> 93.7
    assert "93.7" in packet.executive_summary

    # 2. BLOCKED state
    # Create a new explanation with risk failure
    blocked_explanation = base_explanation.model_copy(update={
        "risk_assessment": RiskAssessment(passed=False, rejection_reasons=["R:R too low"], risk_reward_ratio=0.5)
    })
    packet_blocked = dss.assemble_packet("XAUUSD", blocked_explanation, base_regime, base_macro, {})
    assert packet_blocked.status_level == DecisionStatus.BLOCKED
    assert "BLOCKED" in packet_blocked.executive_summary
    assert "Risk: R:R too low" in packet_blocked.executive_summary

def test_review_flag_logic(dss, base_explanation, base_regime, base_macro):
    """Verify logic for setting the manual review flag."""

    # 1. High score (>80) - No review
    packet_high = dss.assemble_packet("XAUUSD", base_explanation, base_regime, base_macro, {})
    assert packet_high.decision_score > 80.0
    assert packet_high.requires_review is False

    # 2. Lower score (75) - Review Required (even if REVIEW)
    low_conf_regime = base_regime.model_copy(update={"confidence": 0.4})
    # Score: 40 (consensus) + 12 (regime) + 16.6 (risk) + 10 (macro) = 78.6
    packet_mid = dss.assemble_packet("XAUUSD", base_explanation, low_conf_regime, base_macro, {})
    assert 78.0 < packet_mid.decision_score < 79.0
    assert packet_mid.status_level == DecisionStatus.REVIEW
    assert packet_mid.requires_review is True

    # 3. CAUTION status - Always review
    vlow_conf_regime = base_regime.model_copy(update={"confidence": 0.1})
    # Score: 40 + 3 + 16.6 + 10 = 69.6 -> CAUTION
    packet_caution = dss.assemble_packet("XAUUSD", base_explanation, vlow_conf_regime, base_macro, {})
    assert packet_caution.status_level == DecisionStatus.CAUTION
    assert packet_caution.requires_review is True

def test_dashboard_formatting_enhancements(dss, base_explanation, base_regime, base_macro):
    """Verify that new visual elements appear in the dashboard output."""

    # Set to CAUTION to trigger [REVIEW REQUIRED]
    caution_regime = base_regime.model_copy(update={"confidence": 0.1})
    packet = dss.assemble_packet("XAUUSD", base_explanation, caution_regime, base_macro, {})

    output = dss.format_for_operator(packet)
    assert "REVIEW REQUIRED" in output
    assert "Executive Summary" in output
    assert packet.executive_summary[:20] in output

    # Check for High Conviction Badge
    hc_regime = base_regime.model_copy(update={"confidence": 1.0})
    packet_hc = dss.assemble_packet("XAUUSD", base_explanation, hc_regime, base_macro, {})
    assert packet_hc.decision_score >= 90.0

    output_hc = dss.format_for_operator(packet_hc)
    assert "HIGH CONVICTION" in output_hc

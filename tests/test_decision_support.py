"""
Unit tests for the Decision Support System.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.core.constants import SignalDirection
from src.core.decision_support import DecisionSupportSystem
from src.core.explainability import (
    ExecutionSummary,
    ModelAttribution,
    RiskAssessment,
    SignalExplanation,
)
from src.data.event_intelligence import RiskStatus
from src.models.regime_detector import MarketRegime, RegimeInfo


@pytest.fixture
def mock_explanation():
    explanation = MagicMock(spec=SignalExplanation)
    explanation.symbol = "XAUUSD"
    explanation.direction = SignalDirection.BUY
    explanation.total_confidence = 0.8

    explanation.execution_summary = MagicMock(spec=ExecutionSummary)
    explanation.execution_summary.passed = True
    explanation.execution_summary.summary = "All execution filters passed"
    explanation.execution_summary.filters = []

    explanation.risk_assessment = MagicMock(spec=RiskAssessment)
    explanation.risk_assessment.passed = True
    explanation.risk_assessment.rejection_reasons = []
    explanation.risk_assessment.risk_reward_ratio = 2.0
    explanation.risk_assessment.kelly_fraction = 0.02

    # Other fields needed for format_for_terminal integration
    explanation.timestamp = datetime.now(timezone.utc)
    explanation.model_attributions = []
    explanation.feature_contributions = []
    explanation.regime_context = MagicMock()
    explanation.regime_context.regime_name = "Trending"
    explanation.regime_context.volatility_state = "Normal"
    explanation.regime_context.is_favorable = True
    explanation.human_readable_summary = "Test summary"
    explanation.signal_id = 123

    return explanation


@pytest.fixture
def mock_regime():
    return RegimeInfo(
        label=MarketRegime.TRENDING, confidence=0.85, transition_score=0.1, volatility_index=1.2
    )


@pytest.fixture
def mock_macro_risk():
    return RiskStatus(
        is_blocked=False, risk_multiplier=1.0, active_events=[], reason="No active events"
    )


def test_assemble_packet_full_approval(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    performance_metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.1,
        "max_drawdown": 0.05,
        "win_rate": 0.6,
        "total_trades": 100,
    }

    # Setup some model attributions for consensus
    mock_explanation.model_attributions = [
        ModelAttribution(model_name="PPO", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
        ModelAttribution(model_name="LSTM", vote=SignalDirection.BUY, confidence=0.7, weight=0.5),
    ]

    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics=performance_metrics,
    )

    assert packet.symbol == "XAUUSD"
    assert packet.direction == SignalDirection.BUY
    assert packet.consensus == "Unanimous"
    assert packet.is_executable is True
    assert len(packet.blocking_reasons) == 0
    assert packet.performance.sharpe_ratio == 1.5
    assert packet.performance.total_trades == 100


def test_consensus_logic():
    dss = DecisionSupportSystem()
    mock_exp = MagicMock(spec=SignalExplanation)
    mock_exp.direction = SignalDirection.BUY

    # 1. Unanimous
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
        ModelAttribution(model_name="M2", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
    ]
    assert dss._calculate_consensus(mock_exp) == "Unanimous"

    # 2. Strong Majority
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.33),
        ModelAttribution(model_name="M2", vote=SignalDirection.BUY, confidence=0.8, weight=0.33),
        ModelAttribution(model_name="M3", vote=SignalDirection.HOLD, confidence=0.5, weight=0.33),
    ]
    assert dss._calculate_consensus(mock_exp) == "Strong Majority"

    # 3. Mixed Confluence
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
        ModelAttribution(model_name="M2", vote=SignalDirection.SELL, confidence=0.8, weight=0.5),
    ]
    assert dss._calculate_consensus(mock_exp) == "Mixed Confluence"

    # 4. Divided/Weak
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.25),
        ModelAttribution(model_name="M2", vote=SignalDirection.SELL, confidence=0.8, weight=0.25),
        ModelAttribution(model_name="M3", vote=SignalDirection.HOLD, confidence=0.5, weight=0.25),
        ModelAttribution(model_name="M4", vote=SignalDirection.HOLD, confidence=0.5, weight=0.25),
    ]
    assert dss._calculate_consensus(mock_exp) == "Divided/Weak"


def test_assemble_packet_blocked_by_macro(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    mock_macro_risk.is_blocked = True
    mock_macro_risk.reason = "Blocked by FOMC"

    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={},
    )

    assert packet.is_executable is False
    assert any("Macro: Blocked by FOMC" in r for r in packet.blocking_reasons)


def test_assemble_packet_rejected_by_risk(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    mock_explanation.risk_assessment.passed = False
    mock_explanation.risk_assessment.rejection_reasons = ["R:R too low"]

    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={},
    )

    assert packet.is_executable is False
    assert any("Risk: R:R too low" in r for r in packet.blocking_reasons)


def test_format_for_operator(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={"sharpe_ratio": 1.5},
    )

    # Ensure it doesn't crash and returns a string
    output = dss.format_for_operator(packet)
    assert isinstance(output, str)
    assert "XAUUSD" in output
    assert "EXECUTE" in output or "BLOCKED" in output

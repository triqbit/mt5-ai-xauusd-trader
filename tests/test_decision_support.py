"""
Unit tests for the Decision Support System.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.core.decision_support import (
    DecisionSupportSystem,
    DecisionPacket,
    PerformanceContext,
    DecisionStatus,
)
from src.core.explainability import SignalExplanation, ExecutionSummary, RiskAssessment, ModelAttribution
from src.core.constants import SignalDirection
from src.models.regime_detector import RegimeInfo, MarketRegime
from src.data.event_intelligence import RiskStatus, MacroEvent, EventCategory, EventImpact


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
        label=MarketRegime.TRENDING,
        confidence=0.85,
        transition_score=0.1,
        volatility_index=1.2
    )


@pytest.fixture
def mock_macro_risk():
    return RiskStatus(
        is_blocked=False,
        risk_multiplier=1.0,
        active_events=[],
        reason="No active events"
    )


def test_assemble_packet_full_approval(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    performance_metrics = {
        "sharpe_ratio": 1.5,
        "profit_factor": 2.1,
        "recovery_factor": 3.2,
        "max_drawdown": 0.05,
        "win_rate": 0.6,
        "win_loss_ratio": 1.8,
        "total_trades": 100
    }

    # Setup some model attributions for consensus
    mock_explanation.model_attributions = [
        ModelAttribution(model_name="PPO", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
        ModelAttribution(model_name="LSTM", vote=SignalDirection.BUY, confidence=0.7, weight=0.5)
    ]

    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics=performance_metrics
    )

    assert packet.symbol == "XAUUSD"
    assert packet.direction == SignalDirection.BUY
    assert "Unanimous" in packet.consensus
    assert packet.is_executable is True
    assert len(packet.blocking_reasons) == 0
    assert packet.performance.sharpe_ratio == 1.5
    assert packet.performance.recovery_factor == 3.2
    assert packet.performance.win_loss_ratio == 1.8
    assert packet.performance.total_trades == 100

    # Verification of Augmented Fields
    assert packet.status_level == DecisionStatus.EXECUTE
    assert packet.decision_score > 0
    assert packet.sizing_multiplier > 0


def test_decision_augmentation_logic(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()

    # 1. High Confidence Case (Unanimous, High Regime Confidence, Good RR)
    mock_explanation.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.9, weight=1.0)
    ]
    mock_explanation.risk_assessment.risk_reward_ratio = 3.0
    mock_regime = mock_regime.model_copy(update={"confidence": 1.0})
    mock_macro_risk = mock_macro_risk.model_copy(update={"risk_multiplier": 1.0})

    packet = dss.assemble_packet("XAUUSD", mock_explanation, mock_regime, mock_macro_risk, {})
    assert packet.decision_score == 100.0  # (1.0*40) + (1.0*30) + (20 + 10)
    assert packet.status_level == DecisionStatus.EXECUTE
    assert packet.sizing_multiplier == 1.0

    # 2. Caution Case (Low Score)
    mock_explanation.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.5, weight=0.5),
        ModelAttribution(model_name="M2", vote=SignalDirection.SELL, confidence=0.5, weight=0.5),
    ]
    mock_regime = mock_regime.model_copy(update={"confidence": 0.5})
    mock_explanation.risk_assessment.risk_reward_ratio = 1.0  # (1/3)*20 = 6.66
    mock_macro_risk = mock_macro_risk.model_copy(update={"risk_multiplier": 0.5})

    # Consensus score: 0.5 * 40 = 20
    # Regime score: 0.5 * 30 = 15
    # Risk score: 6.66 + 5 = 11.66
    # Total ~ 46.66
    packet = dss.assemble_packet("XAUUSD", mock_explanation, mock_regime, mock_macro_risk, {})
    assert 46.0 < packet.decision_score < 47.0
    assert packet.status_level == DecisionStatus.CAUTION
    # Sizing: (0.4666^1.5) * 0.5 (CAUTION penalty) * 0.5 (Macro multiplier)
    expected_sizing = (packet.decision_score / 100.0) ** 1.5 * 0.5 * 0.5
    assert abs(packet.sizing_multiplier - expected_sizing) < 1e-6

    # 3. Blocked Case
    mock_explanation.risk_assessment.passed = False
    packet = dss.assemble_packet("XAUUSD", mock_explanation, mock_regime, mock_macro_risk, {})
    assert packet.status_level == DecisionStatus.BLOCKED
    assert packet.sizing_multiplier == 0.0

    # 4. Edge Case: Critical Macro Event (Macro multiplier = 0.25)
    mock_explanation.risk_assessment.passed = True
    mock_explanation.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.9, weight=1.0)
    ]
    mock_regime = mock_regime.model_copy(update={"confidence": 1.0})
    mock_explanation.risk_assessment.risk_reward_ratio = 3.0
    mock_macro_risk = mock_macro_risk.model_copy(update={"risk_multiplier": 0.25})

    packet = dss.assemble_packet("XAUUSD", mock_explanation, mock_regime, mock_macro_risk, {})
    # Score: 40 (Consensus) + 30 (Regime) + 20 (R:R) + 2.5 (Macro Safety) = 92.5
    assert packet.decision_score == 92.5
    assert packet.status_level == DecisionStatus.EXECUTE
    # Sizing: (0.925^1.5) * 1.0 (EXECUTE) * 0.25 (Macro)
    expected_sizing = (0.925**1.5) * 0.25
    assert abs(packet.sizing_multiplier - expected_sizing) < 1e-6


def test_consensus_logic():
    dss = DecisionSupportSystem()
    mock_exp = MagicMock(spec=SignalExplanation)
    mock_exp.direction = SignalDirection.BUY

    # 1. Unanimous (Weight: 0.5 + 0.5 = 1.0)
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.5),
        ModelAttribution(model_name="M2", vote=SignalDirection.BUY, confidence=0.8, weight=0.5)
    ]
    assert "Unanimous" in dss._calculate_consensus(mock_exp)

    # 2. Strong Majority (Weight: 0.4 + 0.3 = 0.7 >= 0.66)
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.4),
        ModelAttribution(model_name="M2", vote=SignalDirection.BUY, confidence=0.8, weight=0.3),
        ModelAttribution(model_name="M3", vote=SignalDirection.HOLD, confidence=0.5, weight=0.3)
    ]
    assert "Strong Majority" in dss._calculate_consensus(mock_exp)

    # 3. Mixed Confluence (Weight: 0.51 >= 0.5)
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.51),
        ModelAttribution(model_name="M2", vote=SignalDirection.SELL, confidence=0.8, weight=0.49)
    ]
    assert "Mixed Confluence" in dss._calculate_consensus(mock_exp)

    # 4. Divided/Weak (Weight: 0.49 < 0.5)
    mock_exp.model_attributions = [
        ModelAttribution(model_name="M1", vote=SignalDirection.BUY, confidence=0.8, weight=0.49),
        ModelAttribution(model_name="M2", vote=SignalDirection.SELL, confidence=0.8, weight=0.51)
    ]
    assert "Divided/Weak" in dss._calculate_consensus(mock_exp)

    # 5. No votes
    mock_exp.model_attributions = []
    assert dss._calculate_consensus(mock_exp) == "No Votes"


def test_assemble_packet_blocked_by_macro(mock_explanation, mock_regime, mock_macro_risk):
    dss = DecisionSupportSystem()
    mock_macro_risk = mock_macro_risk.model_copy(update={
        "is_blocked": True,
        "reason": "Blocked by FOMC"
    })

    packet = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={}
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
        performance_metrics={}
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
        performance_metrics={"sharpe_ratio": 1.5}
    )

    # Ensure it doesn't crash and returns a string
    output = dss.format_for_operator(packet)
    assert isinstance(output, str)
    assert "XAUUSD" in output
    assert any(s in output for s in ["EXECUTE", "CAUTION", "BLOCKED"])


def test_performance_metric_color_coding(mock_explanation, mock_regime, mock_macro_risk, mocker):
    """Verify that performance metrics are color-coded in terminal output."""
    from rich.panel import Panel

    dss = DecisionSupportSystem()
    mock_console = MagicMock()

    # 1. Test High Performance (Should be Green)
    packet_high = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={"sharpe_ratio": 2.5, "profit_factor": 2.2, "recovery_factor": 2.1}
    )

    dss.format_for_operator(packet_high, console=mock_console)
    dashboard = mock_console.print.call_args[0][0]

    # Find perf_panel in the dashboard Group
    perf_panel = None
    for r in dashboard.renderables:
        # overview_table is a Table, which contains Panels in its rows
        if hasattr(r, "columns"): # Likely the Table
            # Table doesn't directly expose rows easily in a mockable way without deep diving
            # But we can check all Panels created during the call if we mock Panel
            pass

    # Alternative: Mock Panel where it's used. Since it's imported locally,
    # we patch the 'rich.panel.Panel' class directly.
    mock_panel_cls = mocker.patch("rich.panel.Panel", side_effect=Panel)

    dss.format_for_operator(packet_high, console=mock_console)

    # Find the panel call for "Recent Performance"
    perf_text = ""
    for call in mock_panel_cls.call_args_list:
        if call.kwargs.get("title") == "📊 Recent Performance":
            perf_text = call.args[0]
            break

    assert "[bold green]2.50" in perf_text
    assert "[bold green]2.20" in perf_text
    assert "[bold green]2.10" in perf_text

    # 2. Test Low Performance (Should be Red)
    packet_low = dss.assemble_packet(
        symbol="XAUUSD",
        explanation=mock_explanation,
        regime_info=mock_regime,
        macro_risk=mock_macro_risk,
        performance_metrics={"sharpe_ratio": 0.5, "profit_factor": 0.8, "recovery_factor": 0.2}
    )

    mock_panel_cls.reset_mock()
    dss.format_for_operator(packet_low, console=mock_console)

    perf_text_low = ""
    for call in mock_panel_cls.call_args_list:
        if call.kwargs.get("title") == "📊 Recent Performance":
            perf_text_low = call.args[0]
            break

    assert "[bold red]0.50" in perf_text_low
    assert "[bold red]0.80" in perf_text_low
    assert "[bold red]0.20" in perf_text_low

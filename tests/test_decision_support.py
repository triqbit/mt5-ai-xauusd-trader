"""
Tests for Decision Support module.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.core.decision_support import DecisionSupport, DecisionPacket
from src.core.constants import SignalDirection
from src.core.explainability import SignalExplanation, ExecutionSummary, RiskAssessment, RegimeContext
from src.trading.capital_allocator import AllocationResult
from src.analytics.journal_mining import SessionAnalysis


@pytest.fixture
def mock_explanation():
    return SignalExplanation(
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        total_confidence=0.75,
        execution_summary=ExecutionSummary(passed=True, filters=[], summary="Passed"),
        model_attributions=[],
        feature_contributions=[],
        risk_assessment=RiskAssessment(
            passed=True,
            rejection_reasons=[],
            risk_reward_ratio=2.0,
            drawdown_impact_pct=0.01,
            summary="Safe"
        ),
        regime_context=RegimeContext(
            regime_name="Trending",
            confidence=0.8,
            volatility_state="Normal",
            is_favorable=True,
            summary="Bullish"
        ),
        human_readable_summary="All clear",
        machine_attribution={}
    )

@pytest.fixture
def mock_allocation():
    return AllocationResult(
        strategy_id="ensemble_v1",
        allocated_amount=1000.0,
        allocated_risk_pct=0.01,
        requested_risk_pct=0.01,
        is_allowed=True
    )

@pytest.fixture
def mock_performance():
    return [
        SessionAnalysis(session_name="London", trade_count=10, win_rate=0.6, profit_factor=1.5, is_overtrading=False),
        SessionAnalysis(session_name="New York", trade_count=25, win_rate=0.4, profit_factor=0.8, is_overtrading=True)
    ]

def test_generate_packet_approved(mock_explanation, mock_allocation, mock_performance):
    ds = DecisionSupport()
    packet = ds.generate_packet(mock_explanation, mock_allocation, mock_performance)

    assert isinstance(packet, DecisionPacket)
    assert packet.symbol == "XAUUSD"
    assert packet.is_blocked is False
    assert len(packet.block_reasons) == 0
    assert "APPROVED" in packet.operator_summary
    assert packet.allocation.allocated_amount == 1000.0

def test_generate_packet_blocked_risk(mock_explanation):
    mock_explanation.risk_assessment.passed = False
    mock_explanation.risk_assessment.rejection_reasons = ["Daily loss limit"]

    ds = DecisionSupport()
    packet = ds.generate_packet(mock_explanation)

    assert packet.is_blocked is True
    assert "Daily loss limit" in packet.block_reasons
    assert "BLOCKED" in packet.operator_summary

def test_generate_packet_blocked_execution(mock_explanation):
    mock_explanation.execution_summary.passed = False
    mock_explanation.execution_summary.summary = "High spread"

    ds = DecisionSupport()
    packet = ds.generate_packet(mock_explanation)

    assert packet.is_blocked is True
    assert "Execution: High spread" in packet.block_reasons
    assert "BLOCKED" in packet.operator_summary

def test_generate_packet_blocked_allocation(mock_explanation, mock_allocation):
    mock_allocation.is_allowed = False
    mock_allocation.rejection_reason = "Max heat reached"

    ds = DecisionSupport()
    packet = ds.generate_packet(mock_explanation, mock_allocation)

    assert packet.is_blocked is True
    assert "Allocation: Max heat reached" in packet.block_reasons
    assert "BLOCKED" in packet.operator_summary

def test_format_for_operator(mock_explanation, mock_allocation, mock_performance):
    ds = DecisionSupport()
    packet = ds.generate_packet(mock_explanation, mock_allocation, mock_performance)
    formatted = ds.format_for_operator(packet)

    assert "XAUUSD" in formatted
    assert "BUY" in formatted
    assert "London" in formatted
    assert "New York" in formatted

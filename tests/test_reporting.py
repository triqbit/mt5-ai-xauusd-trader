"""
Tests for the research reporting module.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from src.research.reporting import ResearchReporter, ResearchSummary, PatternReport, AllocationReport
from src.core.trade_logger import TradeLogger
from src.trading.risk_manager import RiskManager

@pytest.fixture
def mock_trade_logger():
    logger = MagicMock(spec=TradeLogger)
    logger.read_performance_report.return_value = {
        "total_trades": 10,
        "win_rate": 0.6,
        "profit_factor": 1.5,
        "sharpe_ratio": 2.0,
        "max_drawdown": 0.1
    }
    return logger

@pytest.fixture
def mock_risk_manager():
    manager = MagicMock(spec=RiskManager)
    return manager

def test_research_summary_json_export():
    summary = ResearchSummary(
        report_id="test_report_001",
        trade_patterns=[
            PatternReport(
                pattern_name="Test Pattern",
                frequency=5,
                win_rate=0.8,
                profit_factor=2.0,
                average_holding_time_minutes=15.0
            )
        ]
    )
    json_out = summary.to_json()
    assert "test_report_001" in json_out
    assert "Test Pattern" in json_out

def test_research_summary_markdown_export():
    summary = ResearchSummary(
        report_id="test_report_002",
        trade_patterns=[
            PatternReport(
                pattern_name="Test Pattern",
                frequency=5,
                win_rate=0.8,
                profit_factor=2.0,
                average_holding_time_minutes=15.0
            )
        ],
        allocations=[
            AllocationReport(
                symbol="XAUUSD",
                current_weight=0.18,
                target_weight=0.18,
                risk_contribution=0.09,
                leverage_used=1.0
            )
        ]
    )
    md_out = summary.to_markdown()
    assert "# Research Summary: test_report_002" in md_out
    assert "Test Pattern" in md_out
    assert "XAUUSD" in md_out
    assert "18.0%" in md_out

def test_research_reporter_generate_summary(mock_trade_logger, mock_risk_manager):
    reporter = ResearchReporter(trade_logger=mock_trade_logger, risk_manager=mock_risk_manager)
    summary = reporter.generate_summary("test_reporter_001")

    assert isinstance(summary, ResearchSummary)
    assert summary.report_id == "test_reporter_001"
    assert len(summary.trade_patterns) > 0
    assert summary.trade_patterns[0].pattern_name == "General Execution"
    assert len(summary.allocations) > 0
    assert any(a.symbol == "XAUUSD" for a in summary.allocations)

def test_research_reporter_no_data():
    reporter = ResearchReporter()
    summary = reporter.generate_summary("empty_report")
    assert summary.report_id == "empty_report"
    assert len(summary.trade_patterns) == 0
    assert len(summary.allocations) == 0

"""
Tests for the research reporting system.
"""

import os
import pytest
from datetime import datetime, timezone
from src.research.reporting import (
    ResearchReport,
    ResearchReporter,
    RegimeSection,
    RegimeSummary,
    StressTestSection,
    StressedMetric,
    AllocationSection,
    AllocationEntry
)

@pytest.fixture
def sample_report():
    return ResearchReport(
        title="Q1 2024 Strategy Robustness Audit",
        executive_summary="The strategy shows high resilience but sensitive to news shocks.",
        regime_analysis=RegimeSection(
            summary="Market was primarily trending with low volatility.",
            regimes=[
                RegimeSummary(label="Trending", frequency_pct=65.0, avg_duration_bars=45, profitability="High"),
                RegimeSummary(label="Ranging", frequency_pct=25.0, avg_duration_bars=12, profitability="Low"),
            ],
            transition_insights="Slow transitions between trending and ranging regimes."
        ),
        stress_tests=StressTestSection(
            resilience_score=85.5,
            baseline=StressedMetric(name="Baseline", total_return="12.5%", max_drawdown="4.2%", sharpe="2.1", outcome="PASS"),
            scenarios=[
                StressedMetric(name="Spread Widening", total_return="10.1%", max_drawdown="5.8%", sharpe="1.8", outcome="PASS"),
                StressedMetric(name="News Shock", total_return="-2.5%", max_drawdown="15.2%", sharpe="-0.5", outcome="FAIL"),
            ],
            fragility_indicators=["High drawdown during volatility spikes"],
            failure_points=["Sudden 50bp price jumps"]
        ),
        allocation_insights=AllocationSection(
            total_heat_pct=45.0,
            allocations=[
                AllocationEntry(name="XAUUSD_PPO", amount="$45,000", heat_pct=45.0, multiplier=1.2)
            ],
            rejection_summary={"Symbol concentration": 5}
        ),
        conclusion="Recommend deploying with reduced size during high-impact news."
    )

def test_markdown_generation(sample_report):
    reporter = ResearchReporter()
    markdown = reporter.generate_markdown(sample_report)

    assert "# Q1 2024 Strategy Robustness Audit" in markdown
    assert "## 1. Market Regime Analysis" in markdown
    assert "Trending" in markdown
    assert "65.0%" in markdown
    assert "## 2. Stress Test Outcomes" in markdown
    assert "Resilience Score" in markdown
    assert "85.5/100" in markdown
    assert "Spread Widening" in markdown
    assert "PASS" in markdown
    assert "## 6. Capital Allocation Insights" in markdown
    assert "XAUUSD_PPO" in markdown
    assert "$45,000" in markdown
    assert "Recommend deploying" in markdown

def test_terminal_formatting(sample_report, capsys):
    reporter = ResearchReporter()
    reporter.format_for_terminal(sample_report)
    captured = capsys.readouterr()

    assert "Q1 2024 Strategy Robustness Audit" in captured.out
    assert "Market Regime Analysis" in captured.out
    assert "Stress Test Outcomes" in captured.out
    assert "Resilience Score: 85.5/100" in captured.out
    assert "Capital Allocation" in captured.out

def test_save_markdown(sample_report, tmp_path):
    reporter = ResearchReporter()
    file_path = tmp_path / "test_report.md"
    reporter.save_markdown(sample_report, str(file_path))

    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        content = f.read()
        assert "Q1 2024 Strategy Robustness Audit" in content

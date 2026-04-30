"""
Tests for the research reporting module.
"""

import datetime
from pathlib import Path
import pytest
from src.research.reporting import (
    ResearchReport,
    RegimeAnalysis,
    StressTestOutcome,
    ResearchReporter,
    HyperparameterRobustness,
    TradePatternFindings,
    ModelDriftObservation,
    AllocationInsight,
    BenchmarkComparison
)

@pytest.fixture
def sample_report():
    return ResearchReport(
        report_id="TEST-2024-001",
        period_start=datetime.date(2024, 1, 1),
        period_end=datetime.date(2024, 1, 31),
        summary="Test summary for research report.",
        regime_analysis=RegimeAnalysis(
            current_regime="Trending Up",
            regime_distribution={"Trending Up": 0.6, "Ranging": 0.4},
            volatility_profile="Moderate",
            regime_shift_detected=True
        ),
        stress_tests=[
            StressTestOutcome(
                scenario_name="Flash Crash",
                max_drawdown=0.05,
                recovery_period_bars=100,
                pnl_impact=-500.0,
                passed=True
            )
        ],
        hyperparameter_robustness=[
            HyperparameterRobustness(
                parameter_name="learning_rate",
                optimal_value=0.0003,
                stability_score=0.85,
                sensitivity_to_noise="Low",
                recommendation="Maintain current value"
            )
        ],
        trade_patterns=[
            TradePatternFindings(
                pattern_name="Morning Gap",
                frequency=12,
                win_rate_impact=0.05,
                significance_score=2.5,
                description="Higher win rate during morning session gaps."
            )
        ],
        model_drift=[
            ModelDriftObservation(
                model_id="PPO-v1",
                metric_name="Accuracy",
                baseline_value=0.55,
                current_value=0.52,
                drift_detected=False,
                drift_score=0.05
            )
        ],
        allocation_insights=[
            AllocationInsight(
                strategy_id="TrendFollower",
                allocated_weight=0.4,
                performance_contribution=0.5,
                marginal_sharpe=1.2,
                over_allocated=False
            )
        ],
        benchmarks=[
            BenchmarkComparison(
                benchmark_name="S&P 500",
                strategy_return=0.1,
                benchmark_return=0.08,
                alpha=0.02,
                beta=0.5,
                tracking_error=0.03
            )
        ]
    )

def test_research_report_validation(sample_report):
    """Verify that the ResearchReport model validates correctly."""
    assert sample_report.report_id == "TEST-2024-001"
    assert len(sample_report.stress_tests) == 1
    assert sample_report.regime_analysis.current_regime == "Trending Up"

def test_markdown_generation(sample_report):
    """Verify that ResearchReporter generates Markdown correctly."""
    reporter = ResearchReporter()
    markdown = reporter.generate_markdown(sample_report)

    assert "# Research Summary: TEST-2024-001" in markdown
    assert "## Executive Summary" in markdown
    assert "## Regime Analysis" in markdown
    assert "Trending Up" in markdown
    assert "Flash Crash" in markdown
    assert "✅ PASS" in markdown
    assert "Morning Gap" in markdown

def test_json_export(sample_report):
    """Verify JSON serialization."""
    json_data = sample_report.to_json()
    assert "TEST-2024-001" in json_data
    assert "regime_analysis" in json_data

def test_file_export(sample_report, tmp_path):
    """Verify exporting to files."""
    reporter = ResearchReporter()
    md_path = reporter.export_to_file(sample_report, tmp_path)

    assert md_path.exists()
    assert (tmp_path / "TEST-2024-001.json").exists()

    content = md_path.read_text()
    assert "TEST-2024-001" in content

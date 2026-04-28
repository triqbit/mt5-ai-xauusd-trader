"""
MT5 AI/ML Trading Bot - Enterprise Edition
tests/test_reporting.py
Unit tests for research reporting engine.
Author : triqbit
License: MIT
"""

import pytest
from datetime import datetime, timezone
from src.research.reporting import (
    ResearchReport,
    RegimeAnalysis,
    StressTestOutcome,
    HyperparameterRobustness,
    TradePattern,
    ModelDrift,
    AllocationInsight,
    BenchmarkComparison
)

def test_research_report_instantiation():
    """Test that ResearchReport can be instantiated with data."""
    report = ResearchReport(
        report_id="TEST-001",
        summary="Automated test report summary.",
        regime_analysis=[
            RegimeAnalysis(
                regime_name="Trending Up",
                prevalence=0.4,
                accuracy=0.65,
                sharpe_ratio=2.1,
                avg_drawdown=0.05,
                notes="Strong performance"
            )
        ],
        stress_tests=[
            StressTestOutcome(
                scenario_name="Flash Crash",
                resilience_score=0.8,
                max_drawdown=0.12,
                recovery_time_steps=50,
                status="PASS",
                observations=["Handled volatility well"]
            )
        ]
    )

    assert report.report_id == "TEST-001"
    assert len(report.regime_analysis) == 1
    assert len(report.stress_tests) == 1
    assert report.author == "ResearchEngine"

def test_report_json_export():
    """Test JSON export functionality."""
    report = ResearchReport(
        report_id="JSON-TEST",
        summary="JSON test summary."
    )
    json_str = report.to_json()
    assert "JSON-TEST" in json_str
    assert "summary" in json_str

def test_report_markdown_export():
    """Test Markdown export functionality and formatting."""
    report = ResearchReport(
        report_id="MD-TEST",
        summary="Markdown test summary.",
        regime_analysis=[
            RegimeAnalysis(
                regime_name="Ranging",
                prevalence=0.5,
                accuracy=0.55,
                sharpe_ratio=1.2,
                avg_drawdown=0.08
            )
        ],
        stress_tests=[
            StressTestOutcome(
                scenario_name="Slippage Stress",
                resilience_score=0.9,
                max_drawdown=0.04,
                recovery_time_steps=10,
                status="PASS"
            )
        ],
        hyperparameter_robustness=[
            HyperparameterRobustness(
                parameter_name="learning_rate",
                optimal_value=0.0003,
                sensitivity_score=0.4,
                oos_consistency=0.85
            )
        ],
        trade_patterns=[
            TradePattern(
                pattern_name="Asian Breakout",
                frequency=120,
                win_rate=0.62,
                profit_factor=1.8,
                significance=0.001
            )
        ],
        model_drift=[
            ModelDrift(
                feature_group="Volatility",
                drift_score=0.05,
                p_value=0.12,
                impact_on_accuracy=-0.02,
                action_required=False
            )
        ],
        allocation_insights=[
            AllocationInsight(
                strategy_name="PPO_XAUUSD",
                current_weight=0.6,
                recommended_weight=0.7,
                reasoning="Strong trend-following performance"
            )
        ],
        benchmarks=[
            BenchmarkComparison(
                benchmark_name="BuyAndHold",
                relative_return=0.15,
                relative_sharpe=0.5,
                win_rate_diff=0.05
            )
        ]
    )

    md = report.to_markdown()

    # Check headers
    assert "# Research Report: MD-TEST" in md
    assert "## 📝 Executive Summary" in md
    assert "## 📊 Market Regime Analysis" in md

    # Check table content
    assert "Ranging" in md
    assert "Slippage Stress" in md
    assert "learning_rate" in md
    assert "Asian Breakout" in md
    assert "Volatility" in md
    assert "PPO_XAUUSD" in md
    assert "BuyAndHold" in md

    # Check formatting (prevalence as percentage)
    assert "50.0%" in md
    # Check formatting (status)
    assert "PASS" in md

def test_report_empty_sections():
    """Test that Markdown export handles empty sections gracefully."""
    report = ResearchReport(
        report_id="EMPTY-TEST",
        summary="Empty sections test."
    )
    md = report.to_markdown()
    assert "N/A" in md
    assert "| N/A |" in md

"""
Integration tests for the research reporting system.
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.analytics.drift_analyzer import DriftAnalysisReport, DriftMetric
from src.analytics.journal_mining import (
    DrawdownCluster,
    JournalReport,
    PatternConcentration,
    SessionAnalysis,
)
from src.models.regime_detector import MarketRegime, RegimeDetector
from src.research.benchmarks import BenchmarkEvaluator
from src.research.hyperopt_walkforward import RobustnessMetrics, WalkForwardResult
from src.research.reporting import ResearchReport, ResearchReporter
from src.research.stress_lab import ResilienceReport, StressTestMetrics
from src.trading.capital_allocator import CapitalAllocator, StrategyConfig


@pytest.fixture
def mock_walk_forward_result():
    return WalkForwardResult(
        best_params={"fast_window": 10, "slow_window": 30},
        metrics=RobustnessMetrics(
            oos_sharpe_mean=1.5,
            oos_sharpe_std=0.2,
            worst_window_sharpe=1.0,
            win_rate_consistency=0.8,
            max_drawdown_consistency=0.7,
            is_oos_gap=0.3,
            stability_penalty=0.1,
            regime_consistency=0.9,
            robustness_score=0.85
        ),
        window_results=[]
    )

@pytest.fixture
def mock_journal_report():
    return JournalReport(
        session_analysis=[
            SessionAnalysis(session_name="London", trade_count=50, win_rate=0.6, profit_factor=2.1, is_overtrading=False),
            SessionAnalysis(session_name="New York", trade_count=80, win_rate=0.4, profit_factor=0.9, is_overtrading=True),
        ],
        volatility_patterns=[],
        drawdown_clusters=[
            DrawdownCluster(start_time=datetime.now(), end_time=datetime.now(), trade_count=4, total_loss=-1500.0)
        ],
        profitable_concentrations=[
            PatternConcentration(attribute="algorithm", value="PPO", win_rate=0.65, profit_factor=2.5, total_trades=100)
        ],
        risk_block_summary=[]
    )

@pytest.fixture
def mock_capital_allocator():
    allocator = CapitalAllocator(total_budget=100000.0)
    allocator.add_strategy(StrategyConfig(strategy_id="PPO_XAUUSD", symbol="XAUUSD", model_family="RL", capital_cap=50000.0))
    allocator.update_allocation("PPO_XAUUSD", 25000.0)
    return allocator

@pytest.fixture
def mock_regime_df():
    return pd.DataFrame({
        "close": np.linspace(2000, 2100, 100),
        "regime": [MarketRegime.TRENDING.value] * 100,
        "returns": [0.001] * 100
    })

@pytest.fixture
def mock_drift_report():
    return DriftAnalysisReport(
        metrics=[
            DriftMetric(name="Feature A", baseline_value=0.5, current_value=0.55, drift_score=0.1, is_significant=False),
            DriftMetric(name="Feature B", baseline_value=10.0, current_value=15.0, drift_score=0.5, is_significant=True),
        ],
        feature_importance_shifts={"Feature B": 0.15, "Feature C": -0.1},
        overall_drift_status="WARNING"
    )

@pytest.fixture
def mock_resilience_report():
    baseline = StressTestMetrics(total_return=0.15, max_drawdown=0.05, sharpe_ratio=2.0, win_rate=0.6, num_trades=100, execution_quality_score=1.0, latency_impact=0.0)
    return ResilienceReport(
        strategy_name="PPO_Agent",
        baseline_metrics=baseline,
        scenario_results={
            "High Slippage": StressTestMetrics(total_return=0.08, max_drawdown=0.12, sharpe_ratio=1.1, win_rate=0.55, num_trades=95, execution_quality_score=0.9, latency_impact=0.05),
            "Flash Crash": StressTestMetrics(total_return=-0.05, max_drawdown=0.25, sharpe_ratio=-0.2, win_rate=0.4, num_trades=90, execution_quality_score=0.8, latency_impact=0.1)
        },
        resilience_score=65.0,
        fragility_indicators=["High sensitivity to slippage"],
        failure_points=["Flash crash events"],
        degradation_summary="Strategy degrades under extreme volatility."
    )

@pytest.fixture
def mock_benchmark_evaluator():
    df = pd.DataFrame({"close": np.linspace(2000, 2100, 100)})
    evaluator = BenchmarkEvaluator(df)
    # Manually inject results since evaluate_all requires real strategy objects
    evaluator.results["Baseline_EMA"] = {"Total Return": 0.05, "Sharpe Ratio": 1.0, "Max Drawdown": 0.1}
    evaluator.results["My_Strategy"] = {"Total Return": 0.12, "Sharpe Ratio": 2.1, "Max Drawdown": 0.04}
    evaluator.results["My_Strategy_returns"] = np.random.normal(0.001, 0.01, 100)
    evaluator.results["Baseline_EMA_returns"] = np.random.normal(0.0005, 0.01, 100)
    return evaluator

def test_full_report_generation(mock_walk_forward_result, mock_journal_report, mock_capital_allocator, mock_regime_df, mock_drift_report, mock_resilience_report, mock_benchmark_evaluator):
    regime_detector = RegimeDetector()

    # 1. Assemble report from components
    report = ResearchReport(
        title="Full Strategy Audit",
        executive_summary="The strategy is performing well in trending markets but overtrades in NY session.",
        regime_analysis=regime_detector.generate_summary(mock_regime_df),
        stress_tests=mock_resilience_report.to_report_section(),
        hyperparameter_robustness=mock_walk_forward_result.to_report_section(),
        trade_patterns=mock_journal_report.to_report_section(),
        model_drift=mock_drift_report.to_report_section(),
        allocation_insights=mock_capital_allocator.to_report_section(rejection_history={"Heat Limit": 3}),
        benchmarks=mock_benchmark_evaluator.to_report_section("Baseline_EMA"),
        conclusion="Focus on London session and reduce risk during NY."
    )

    reporter = ResearchReporter()

    # 2. Verify Markdown Generation
    md_content = reporter.generate_markdown(report)
    assert "# Full Strategy Audit" in md_content
    assert "Table of Contents" in md_content
    assert "Market Regime Analysis" in md_content
    assert "trending" in md_content
    assert "Hyperparameter Robustness" in md_content
    assert "fast_window" in md_content
    assert "Trade Pattern Findings" in md_content
    assert "Overtrading" in md_content
    assert "Capital Allocation Insights" in md_content
    assert "PPO_XAUUSD" in md_content
    assert "Heat Limit: 3" in md_content

    # 3. Verify HTML Generation
    html_content = reporter.generate_html(report)
    assert "<title>Full Strategy Audit - Research Report</title>" in html_content
    assert "<h1>Full Strategy Audit</h1>" in html_content
    assert "25.0%" in html_content # Heat from 25000/100000
    assert "Overtrading" in html_content
    assert "trending" in html_content

def test_save_html(mock_walk_forward_result, tmp_path):
    report = ResearchReport(
        title="Save Test",
        executive_summary="Testing save functionality.",
        hyperparameter_robustness=mock_walk_forward_result.to_report_section(),
        conclusion="Done."
    )
    reporter = ResearchReporter()
    file_path = tmp_path / "test_report.html"
    reporter.save_html(report, str(file_path))

    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        content = f.read()
        assert "<!DOCTYPE html>" in content
        assert "Save Test" in content

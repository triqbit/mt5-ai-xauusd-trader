"""
MT5 AI/ML Trading Bot - Backtest to Reporting Integration Test
tests/test_backtest_reporting_pipeline.py

Verifies the high-value integration path:
Data Generation -> Backtest Engine -> Benchmark Evaluation -> Stress Testing -> Research Reporting
"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.core.feature_engineering import FeatureEngineer
from src.research.benchmarks import BenchmarkEvaluator
from src.research.reporting import ResearchOrchestrator, ResearchReporter
from src.research.stress_lab import StressLab, StressTestMetrics
from src.trading.backtester import BacktestEngine
from src.utils.synthetic_data import ScenarioGenerator


@pytest.fixture
def data_generator():
    return ScenarioGenerator(seed=42)

@pytest.fixture
def feature_engineer():
    return FeatureEngineer(base_timeframe="M5", timeframes=["M15"])

@pytest.fixture
def reporter():
    return ResearchReporter()

class SimpleMockModel:
    def __init__(self, direction=1):
        self.direction = direction
        self.name = "MockModel"
    def predict(self, obs, **kwargs):
        if isinstance(obs, pd.DataFrame):
            return np.full(len(obs), self.direction)
        return type("Signal", (), {"direction": self.direction, "confidence": 0.9})

def test_backtest_to_reporting_flow(data_generator, feature_engineer, reporter, tmp_path):
    # 1. Generate Data
    n_steps = 1000
    df = data_generator.generate(n_steps=n_steps, regime="trending")
    df.index = pd.date_range(start="2024-01-01", periods=n_steps, freq="5min")

    # 2. Run Backtest
    model = SimpleMockModel(direction=1)
    engine = BacktestEngine(
        symbol="XAUUSD",
        feature_engineer=feature_engineer,
        initial_balance=10000.0,
        spread=0.1
    )
    engine.ef = MagicMock()
    engine.ef.validate.return_value = MagicMock(is_approved=True)

    backtest_report = engine.run_walk_forward(
        df,
        model,
        train_window=200,
        test_window=100,
        step_size=100
    )
    assert backtest_report.total_trades > 0

    # 3. Evaluate Benchmarks
    evaluator = BenchmarkEvaluator(df)
    evaluator.results["MockModel"] = {
        "Total Return": backtest_report.total_return,
        "Sharpe Ratio": backtest_report.sharpe_ratio,
        "Max Drawdown": backtest_report.max_drawdown,
        "Win Rate": backtest_report.win_rate,
        "Profit Factor": backtest_report.profit_factor,
        "Num Trades": backtest_report.total_trades
    }
    evaluator.results["MockModel_returns"] = np.random.normal(0.001, 0.01, n_steps)
    evaluator.results["Baseline_EMA"] = {
        "Total Return": 0.05, "Sharpe Ratio": 1.0, "Max Drawdown": 0.1, "Num Trades": 50
    }
    evaluator.results["Baseline_EMA_returns"] = np.random.normal(0.0005, 0.01, n_steps)

    # 4. Run Stress Lab
    stress_lab = StressLab(strategy=model, data=df)
    baseline_stress_metrics = StressTestMetrics(
        total_return=backtest_report.total_return,
        max_drawdown=backtest_report.max_drawdown,
        sharpe_ratio=backtest_report.sharpe_ratio,
        win_rate=backtest_report.win_rate,
        num_trades=backtest_report.total_trades,
        execution_quality_score=1.0,
        latency_impact=0.0
    )
    resilience_report = stress_lab.run_standard_suite(baseline_stress_metrics)

    # 5. Assemble Research Report
    orchestrator = ResearchOrchestrator(
        title="Integration Test Audit",
        executive_summary="Automated integration test for backtest-to-reporting flow.",
        conclusion="Workflow is functional."
    )
    orchestrator.add_section(resilience_report.to_report_section())
    orchestrator.add_section(evaluator.to_report_section(baseline_name="Baseline_EMA"))

    report = orchestrator.build()
    md_report = reporter.generate_markdown(report)
    html_report = reporter.generate_html(report)

    # Final Assertions
    assert report.title == "Integration Test Audit"
    assert "## 2. Stress Test Outcomes" in md_report
    assert "MockModel" in html_report

    expected_return_str = f"{backtest_report.total_return * 100:.2f}%"
    assert expected_return_str in md_report

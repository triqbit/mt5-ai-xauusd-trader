import json
from datetime import datetime

import pytest

from src.models.market_regime import MarketRegime
from src.research.reporting import (
    AllocationInsight,
    BenchmarkComp,
    HyperparamRobustness,
    ModelDrift,
    RegimeStats,
    ResearchReport,
    StressTestResult,
    TradePattern,
)


def test_research_report_generation():
    report = ResearchReport(
        title="XAUUSD Strategy Performance Q1 2026",
        executive_summary="The strategy showed strong resilience across different market regimes, with a notable alpha in trending environments.",
        regimes=[
            RegimeStats(
                regime=MarketRegime.TRENDING,
                count=150,
                avg_profit=12.5,
                win_rate=0.62,
                max_dd=4.5,
            ),
            RegimeStats(
                regime=MarketRegime.RANGING,
                count=300,
                avg_profit=2.1,
                win_rate=0.51,
                max_dd=8.2,
            ),
        ],
        stress_tests=[
            StressTestResult(
                scenario="Flash Crash",
                score=0.85,
                max_dd=12.0,
                recovery="45 mins",
                outcome="PASSED",
            )
        ],
        hyperparams=[
            HyperparamRobustness(
                param="Learning Rate", value=0.0003, stability=0.92, range="[0.0001, 0.001]"
            )
        ],
        patterns=[
            TradePattern(
                pattern_id="London Open Breakout",
                frequency=42,
                edge=15.2,
                significance=0.04,
                status="VALIDATED",
            )
        ],
        drift=[
            ModelDrift(
                model="PPO_v2",
                error=0.024,
                psi=0.12,
                decay=0.05,
                action="MONITOR",
            )
        ],
        allocations=[
            AllocationInsight(
                strategy="TrendFollowing",
                capital=50000.0,
                utilisation=0.75,
                risk_contrib=0.60,
                multiplier=1.2,
            )
        ],
        benchmarks=[
            BenchmarkComp(
                metric="Sharpe Ratio",
                system_val=2.1,
                bench_val=1.4,
                alpha=0.5,
            )
        ],
    )

    markdown = report.to_markdown()
    assert "# Institutional Research Summary: XAUUSD Strategy Performance Q1 2026" in markdown
    assert "TRENDING" in markdown
    assert "Flash Crash" in markdown
    assert "PPO_v2" in markdown
    assert "TrendFollowing" in markdown
    assert "Sharpe Ratio" in markdown

    data = json.loads(report.to_json())
    assert data["title"] == "XAUUSD Strategy Performance Q1 2026"
    assert len(data["regimes"]) == 2


def test_research_report_empty_sections():
    report = ResearchReport(
        title="Empty Report",
        executive_summary="Nothing happened.",
    )
    markdown = report.to_markdown()
    assert "_No data available for this section._" in markdown
    assert "## 2. Market Regime Analysis" in markdown

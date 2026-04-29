"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Structured research reporting engine.
Author : triqbit
License: MIT
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field

from src.models.market_regime import MarketRegime
from src.research import templates


class RegimeStats(BaseModel):
    regime: MarketRegime
    count: int
    avg_profit: float
    win_rate: float
    max_dd: float


class StressTestResult(BaseModel):
    scenario: str
    score: float
    max_dd: float
    recovery: str
    outcome: str


class HyperparamRobustness(BaseModel):
    param: str
    value: Any
    stability: float
    range: str


class TradePattern(BaseModel):
    pattern_id: str
    frequency: int
    edge: float
    significance: float
    status: str


class ModelDrift(BaseModel):
    model: str
    error: float
    psi: float
    decay: float
    action: str


class AllocationInsight(BaseModel):
    strategy: str
    capital: float
    utilisation: float
    risk_contrib: float
    multiplier: float


class BenchmarkComp(BaseModel):
    metric: str
    system_val: float
    bench_val: float
    alpha: float


class ResearchReport(BaseModel):
    title: str
    author: str = "triqbit"
    version: str = "1.0.0"
    date: datetime = Field(default_factory=datetime.now)
    executive_summary: str
    regimes: List[RegimeStats] = []
    stress_tests: List[StressTestResult] = []
    hyperparams: List[HyperparamRobustness] = []
    patterns: List[TradePattern] = []
    drift: List[ModelDrift] = []
    allocations: List[AllocationInsight] = []
    benchmarks: List[BenchmarkComp] = []

    def to_markdown(self) -> str:
        """Generates a high-quality Markdown report."""

        def format_table(header: str, rows: List[str]) -> str:
            if not rows:
                return "_No data available for this section._"
            divider = "| " + " | ".join(["---"] * (header.count("|") - 1)) + " |"
            return "\n".join([header, divider, *rows])

        regime_rows = [
            templates.REGIME_TABLE_ROW.format(**r.model_dump()) for r in self.regimes
        ]
        stress_rows = [
            templates.STRESS_TEST_TABLE_ROW.format(**s.model_dump())
            for s in self.stress_tests
        ]
        hyper_rows = [
            templates.HYPEROPT_TABLE_ROW.format(**h.model_dump())
            for h in self.hyperparams
        ]
        pattern_rows = [
            templates.TRADE_PATTERN_TABLE_ROW.format(**p.model_dump())
            for p in self.patterns
        ]
        drift_rows = [
            templates.DRIFT_TABLE_ROW.format(**d.model_dump()) for d in self.drift
        ]
        alloc_rows = [
            templates.ALLOCATION_TABLE_ROW.format(**a.model_dump())
            for a in self.allocations
        ]
        bench_rows = [
            templates.BENCHMARK_TABLE_ROW.format(**b.model_dump())
            for b in self.benchmarks
        ]

        return templates.MAIN_REPORT_TEMPLATE.format(
            title=self.title,
            date=self.date.strftime("%Y-%m-%d %H:%M"),
            author=self.author,
            version=self.version,
            executive_summary=self.executive_summary,
            regime_analysis=format_table(templates.REGIME_TABLE_HEADER, regime_rows),
            stress_tests=format_table(templates.STRESS_TEST_TABLE_HEADER, stress_rows),
            hyperparameter_robustness=format_table(
                templates.HYPEROPT_TABLE_HEADER, hyper_rows
            ),
            trade_patterns=format_table(
                templates.TRADE_PATTERN_TABLE_HEADER, pattern_rows
            ),
            model_drift=format_table(templates.DRIFT_TABLE_HEADER, drift_rows),
            allocation_insights=format_table(
                templates.ALLOCATION_TABLE_HEADER, alloc_rows
            ),
            benchmarks=format_table(templates.BENCHMARK_TABLE_HEADER, bench_rows),
        )

    def to_json(self) -> str:
        """Exports the report data as JSON."""
        return self.model_dump_json(indent=2)

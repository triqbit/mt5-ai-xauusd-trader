"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Structured research reporting engine.
Author : triqbit
License: MIT
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RegimeAnalysis(BaseModel):
    """Analysis of market regimes and model performance within them."""

    regime_name: str
    prevalence: float  # Percentage of time in this regime
    accuracy: float
    sharpe_ratio: float
    avg_drawdown: float
    notes: Optional[str] = ""


class StressTestOutcome(BaseModel):
    """Outcome of a specific stress scenario."""

    scenario_name: str
    resilience_score: float  # 0.0 to 1.0
    max_drawdown: float
    recovery_time_steps: int
    status: str  # e.g., "PASS", "FAIL", "WARNING"
    observations: List[str] = Field(default_factory=list)


class HyperparameterRobustness(BaseModel):
    """Stability analysis of hyperparameters across windows."""

    parameter_name: str
    optimal_value: Any
    sensitivity_score: float  # High score means performance changes significantly with small param changes
    oos_consistency: float  # Performance consistency in Out-of-Sample windows


class TradePattern(BaseModel):
    """Insights derived from trade history mining."""

    pattern_name: str
    frequency: int
    win_rate: float
    profit_factor: float
    significance: float  # Statistical significance p-value or similar


class ModelDrift(BaseModel):
    """Observations on model performance or input distribution drift."""

    feature_group: str
    drift_score: float  # Quantitative measure of drift
    p_value: float
    impact_on_accuracy: float
    action_required: bool


class AllocationInsight(BaseModel):
    """Insights into capital allocation and strategy weighting."""

    strategy_name: str
    current_weight: float
    recommended_weight: float
    reasoning: str


class BenchmarkComparison(BaseModel):
    """Comparison against baseline strategies."""

    benchmark_name: str
    relative_return: float
    relative_sharpe: float
    win_rate_diff: float


class ResearchReport(BaseModel):
    """Comprehensive institutional research report."""

    report_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    author: str = "ResearchEngine"
    summary: str

    regime_analysis: List[RegimeAnalysis] = Field(default_factory=list)
    stress_tests: List[StressTestOutcome] = Field(default_factory=list)
    hyperparameter_robustness: List[HyperparameterRobustness] = Field(default_factory=list)
    trade_patterns: List[TradePattern] = Field(default_factory=list)
    model_drift: List[ModelDrift] = Field(default_factory=list)
    allocation_insights: List[AllocationInsight] = Field(default_factory=list)
    benchmarks: List[BenchmarkComparison] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Export report to JSON string."""
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        """Export report to Markdown using templates."""
        from src.research.templates import RESEARCH_REPORT_TEMPLATE

        regime_rows = "\n".join(
            f"| {r.regime_name} | {r.prevalence:.1%} | {r.accuracy:.2f} | {r.sharpe_ratio:.2f} | {r.avg_drawdown:.2%} | {r.notes} |"
            for r in self.regime_analysis
        )
        stress_rows = "\n".join(
            f"| {s.scenario_name} | {s.resilience_score:.2f} | {s.max_drawdown:.2%} | {s.recovery_time_steps} | {s.status} | {', '.join(s.observations)} |"
            for s in self.stress_tests
        )
        hyper_rows = "\n".join(
            f"| {h.parameter_name} | {h.optimal_value} | {h.sensitivity_score:.2f} | {h.oos_consistency:.2f} |"
            for h in self.hyperparameter_robustness
        )
        pattern_rows = "\n".join(
            f"| {p.pattern_name} | {p.frequency} | {p.win_rate:.1%} | {p.profit_factor:.2f} | {p.significance:.4f} |"
            for p in self.trade_patterns
        )
        drift_rows = "\n".join(
            f"| {d.feature_group} | {d.drift_score:.4f} | {d.p_value:.4f} | {d.impact_on_accuracy:.2%} | {'YES' if d.action_required else 'NO'} |"
            for d in self.model_drift
        )
        allocation_rows = "\n".join(
            f"| {a.strategy_name} | {a.current_weight:.1%} | {a.recommended_weight:.1%} | {a.reasoning} |"
            for a in self.allocation_insights
        )
        benchmark_rows = "\n".join(
            f"| {b.benchmark_name} | {b.relative_return:+.2%} | {b.relative_sharpe:+.2f} | {b.win_rate_diff:+.2%} |"
            for b in self.benchmarks
        )

        return RESEARCH_REPORT_TEMPLATE.format(
            report_id=self.report_id,
            author=self.author,
            timestamp=self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            summary=self.summary,
            regime_rows=regime_rows if regime_rows else "| N/A | | | | | |",
            stress_rows=stress_rows if stress_rows else "| N/A | | | | | |",
            hyper_rows=hyper_rows if hyper_rows else "| N/A | | | |",
            pattern_rows=pattern_rows if pattern_rows else "| N/A | | | | |",
            drift_rows=drift_rows if drift_rows else "| N/A | | | | |",
            allocation_rows=allocation_rows if allocation_rows else "| N/A | | | |",
            benchmark_rows=benchmark_rows if benchmark_rows else "| N/A | | |",
        )

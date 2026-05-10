"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Institutional-grade research reporting system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# --- Pydantic Models for Sections ---


class RegimeSummary(BaseModel):
    label: str
    frequency_pct: float
    avg_duration_bars: int
    profitability: str


class RegimeSection(BaseModel):
    summary: str
    regimes: list[RegimeSummary]
    transition_insights: str


class StressedMetric(BaseModel):
    name: str
    total_return: str
    max_drawdown: str
    sharpe: str
    recovery_factor: str = "0.00"
    profit_factor: str = "0.00"
    outcome: str


class StressTestSection(BaseModel):
    resilience_score: float
    baseline: StressedMetric
    scenarios: list[StressedMetric]
    fragility_indicators: list[str]
    failure_points: list[str]


class ParameterRobustness(BaseModel):
    name: str
    range: str
    optimal: str
    sensitivity: str


class HyperparameterSection(BaseModel):
    stability_score: float
    parameters: list[ParameterRobustness]
    insights: str


class PatternConcentration(BaseModel):
    attribute: str
    value: str
    win_rate: float
    profit_factor: float
    total_trades: int = 0


class BehavioralRisk(BaseModel):
    type: str
    description: str


class SignalMotif(BaseModel):
    algorithm: str
    direction: int
    volatility_bucket: str
    confidence_bucket: str
    session: str = "Unknown"
    frequency: int
    win_rate: float
    cluster_frequency: int = 0


class TradePatternSection(BaseModel):
    primary_insight: str
    concentrations: list[PatternConcentration]
    behavioral_risks: list[BehavioralRisk]
    motifs: list[SignalMotif] = Field(default_factory=list)
    avg_win_duration: float = 0.0
    avg_loss_duration: float = 0.0


class DriftMetric(BaseModel):
    name: str
    baseline: str
    current: str
    drift_pct: float
    status: str


class ModelDriftSection(BaseModel):
    metrics: list[DriftMetric]
    feature_shifts: str


class AllocationEntry(BaseModel):
    name: str
    amount: str
    heat_pct: float
    multiplier: float


class AllocationSection(BaseModel):
    total_heat_pct: float
    allocations: list[AllocationEntry]
    rejection_summary: dict[str, int]
    diversification_score: float = 1.0


class BenchmarkComparison(BaseModel):
    name: str
    total_return: str
    sharpe: str
    max_drawdown: str
    p_value: str
    profit_factor: str = "0.00"
    sqn: str = "0.00"
    recovery_factor: str = "0.00"


class BenchmarkSection(BaseModel):
    comparisons: list[BenchmarkComparison]
    statistical_summary: str


class RLMetric(BaseModel):
    agent_name: str
    sharpe: float
    sortino: float = 0.0
    profit_factor: float
    max_dd: float
    win_rate: float
    calmar: float = 0.0
    stability_score: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    recovery_factor: float = 0.0
    ulcer_index: float = 0.0
    sqn: float = 0.0
    tail_ratio: float = 0.0
    common_sense_ratio: float = 0.0
    gain_to_pain_ratio: float = 0.0
    lake_ratio: float = 0.0
    portfolio_heat: float = 0.0


class RLSection(BaseModel):
    comparison_summary: str
    best_agent: str
    performance_gap: float
    metrics: list[RLMetric]


class RareEventSummary(BaseModel):
    event_type: str
    peak_impact_pct: float
    realized_volatility: float
    recovery_attained: float
    description: str = ""


class RareEventSection(BaseModel):
    scenarios: list[RareEventSummary]
    insights: str


class CalibrationBucket(BaseModel):
    range: str
    accuracy: float
    confidence: float
    samples: int


class CalibrationSection(BaseModel):
    brier_score: float
    ece: float
    mce: float
    status: str
    optimal_threshold: float
    buckets: list[CalibrationBucket]
    reliability_insight: str


class ExecutionMetric(BaseModel):
    name: str
    value: str
    status: str


class ExecutionQualitySection(BaseModel):
    efficiency_score: float
    metrics: list[ExecutionMetric]
    opportunity_cost: str
    trade_count: int
    rejected_count: int


# --- Full Report Model ---


class ResearchReport(BaseModel):
    """Structured research report container."""

    title: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author: str = "Jules Research"
    overall_status: str = "PROVISIONAL"
    executive_summary: str

    regime_analysis: RegimeSection | None = None
    stress_tests: StressTestSection | None = None
    hyperparameter_robustness: HyperparameterSection | None = None
    trade_patterns: TradePatternSection | None = None
    model_drift: ModelDriftSection | None = None
    allocation_insights: AllocationSection | None = None
    benchmarks: BenchmarkSection | None = None
    rl_evaluation: RLSection | None = None
    rare_events: RareEventSection | None = None
    calibration_analysis: CalibrationSection | None = None
    execution_quality: ExecutionQualitySection | None = None

    conclusion: str
    recommendations: list[str] = Field(default_factory=list)


class ResearchReporter:
    """
    Orchestrator for generating research reports.
    Supports terminal display (rich) and Markdown export (jinja2).
    """

    def __init__(self, template_dir: str | None = None):
        if not template_dir:
            # Default to relative path from this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(base_dir, "templates")

        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.console = Console()

    def generate_markdown(self, report: ResearchReport) -> str:
        """Render the report as a Markdown string."""
        template = self.jinja_env.get_template("research_report.md.j2")
        return template.render(report.model_dump())

    def save_markdown(self, report: ResearchReport, filepath: str) -> None:
        """Save the report to a Markdown file."""
        content = self.generate_markdown(report)
        with open(filepath, "w") as f:
            f.write(content)

    def generate_html(self, report: ResearchReport) -> str:
        """Render the report as an HTML string."""
        template = self.jinja_env.get_template("research_report.html.j2")
        return template.render(report.model_dump())

    def save_html(self, report: ResearchReport, filepath: str) -> None:
        """Save the report to an HTML file."""
        content = self.generate_html(report)
        with open(filepath, "w") as f:
            f.write(content)

    def _get_color_for_metric(self, value: str | float, metric_type: str) -> str:
        """Get Rich color code based on institutional thresholds."""
        try:
            # Handle percentage strings or raw numbers
            if isinstance(value, str):
                cleaned = value.replace("%", "").replace("$", "").replace(",", "")
                val = float(cleaned)
                if "%" in value:
                    val /= 100.0
            else:
                val = float(value)
        except (ValueError, TypeError):
            return "white"

        if metric_type == "sharpe":
            if val >= 2.0:
                return "green"
            if val >= 1.0:
                return "yellow"
            return "red"
        if metric_type == "pf":
            if val >= 2.0:
                return "green"
            if val >= 1.5:
                return "yellow"
            return "red"
        if metric_type == "recovery":
            if val >= 3.0:
                return "green"
            if val >= 2.0:
                return "yellow"
            return "red"
        if metric_type == "win_rate":
            if val >= 0.55:
                return "green"
            if val >= 0.45:
                return "yellow"
            return "red"
        return "white"

    def format_for_terminal(self, report: ResearchReport) -> None:
        """Print a scannable version of the report to the terminal."""
        status_color = "green" if report.overall_status == "VERIFIED" else "yellow"
        self.console.print(
            Panel(
                f"[bold blue]{report.title}[/]\n"
                f"[dim]Date: {report.timestamp} | Author: {report.author}[/]\n"
                f"Status: [{status_color}]{report.overall_status}[/]"
            )
        )

        self.console.print("\n[bold]Executive Summary[/]")
        self.console.print(report.executive_summary)

        section_idx = 1
        if report.regime_analysis:
            self.console.print(f"\n[bold cyan]{section_idx}. Market Regime Analysis[/]")
            section_idx += 1
            table = Table(box=None)
            table.add_column("Regime")
            table.add_column("Frequency")
            table.add_column("Profitability")
            for r in report.regime_analysis.regimes:
                table.add_row(r.label, f"{r.frequency_pct}%", r.profitability)
            self.console.print(table)

        if report.stress_tests:
            self.console.print(f"\n[bold red]{section_idx}. Stress Test Outcomes[/]")
            section_idx += 1
            self.console.print(
                f"Resilience Score: [bold]{report.stress_tests.resilience_score}/100[/]"
            )
            table = Table(box=None)
            table.add_column("Scenario")
            table.add_column("Return")
            table.add_column("MaxDD")
            table.add_column("Recov")
            table.add_column("PF")
            table.add_column("Outcome")

            # Baseline row
            b = report.stress_tests.baseline
            table.add_row(
                "Baseline",
                b.total_return,
                b.max_drawdown,
                f"[{self._get_color_for_metric(b.recovery_factor, 'recovery')}]{b.recovery_factor}[/]",
                f"[{self._get_color_for_metric(b.profit_factor, 'pf')}]{b.profit_factor}[/]",
                "N/A",
            )
            for s in report.stress_tests.scenarios:
                table.add_row(
                    s.name,
                    s.total_return,
                    s.max_drawdown,
                    f"[{self._get_color_for_metric(s.recovery_factor, 'recovery')}]{s.recovery_factor}[/]",
                    f"[{self._get_color_for_metric(s.profit_factor, 'pf')}]{s.profit_factor}[/]",
                    s.outcome,
                )
            self.console.print(table)

        if report.hyperparameter_robustness:
            self.console.print(f"\n[bold magenta]{section_idx}. Hyperparameter Robustness[/]")
            section_idx += 1
            self.console.print(
                f"Stability Score: [bold]{report.hyperparameter_robustness.stability_score}/100[/]"
            )
            table = Table(box=None)
            table.add_column("Parameter")
            table.add_column("Optimal")
            table.add_column("Sensitivity")
            for p in report.hyperparameter_robustness.parameters:
                table.add_row(p.name, p.optimal, p.sensitivity)
            self.console.print(table)

        if report.trade_patterns:
            self.console.print(f"\n[bold yellow]{section_idx}. Trade Pattern Findings[/]")
            section_idx += 1
            self.console.print(f"Insight: {report.trade_patterns.primary_insight}")
            self.console.print(
                f"[dim]Avg Win Duration: {report.trade_patterns.avg_win_duration:.1f}m | "
                f"Avg Loss Duration: {report.trade_patterns.avg_loss_duration:.1f}m[/]"
            )
            table = Table(box=None)
            table.add_column("Attribute")
            table.add_column("Value")
            table.add_column("WR")
            table.add_column("PF")
            table.add_column("Trades")
            for c in report.trade_patterns.concentrations:
                wr_color = self._get_color_for_metric(c.win_rate, "win_rate")
                pf_color = self._get_color_for_metric(c.profit_factor, "pf")
                table.add_row(
                    c.attribute,
                    c.value,
                    f"[{wr_color}]{c.win_rate:.1%}[/]",
                    f"[{pf_color}]{c.profit_factor:.2f}[/]",
                    str(c.total_trades),
                )
            self.console.print(table)

            if report.trade_patterns.motifs:
                self.console.print("[dim]Signal Motifs (Losing Combinations):[/]")
                m_table = Table(box=None)
                m_table.add_column("Algo")
                m_table.add_column("Vol")
                m_table.add_column("Conf")
                m_table.add_column("WR")
                for m in report.trade_patterns.motifs:
                    if m.win_rate < 0.5:
                        wr_color = self._get_color_for_metric(m.win_rate, 'win_rate')
                        m_table.add_row(
                            m.algorithm,
                            m.volatility_bucket,
                            m.confidence_bucket,
                            f"[{wr_color}]{m.win_rate:.1%}[/]",
                        )
                self.console.print(m_table)

        if report.model_drift:
            self.console.print(f"\n[bold blue]{section_idx}. Model Drift Observations[/]")
            section_idx += 1
            table = Table(box=None)
            table.add_column("Metric")
            table.add_column("Drift %")
            table.add_column("Status")
            for m in report.model_drift.metrics:
                table.add_row(m.name, f"{m.drift_pct}%", m.status)
            self.console.print(table)

        if report.allocation_insights:
            self.console.print(f"\n[bold green]{section_idx}. Capital Allocation[/]")
            section_idx += 1
            self.console.print(
                f"Total Heat: {report.allocation_insights.total_heat_pct}% | Diversification: {report.allocation_insights.diversification_score:.2f}"
            )
            table = Table(box=None)
            table.add_column("Target")
            table.add_column("Amount")
            table.add_column("Heat")
            for a in report.allocation_insights.allocations:
                table.add_row(a.name, a.amount, f"{a.heat_pct}%")
            self.console.print(table)

        if report.benchmarks:
            self.console.print(f"\n[bold white]{section_idx}. Benchmark Comparisons[/]")
            section_idx += 1
            table = Table(box=None)
            table.add_column("Strategy")
            table.add_column("Return")
            table.add_column("Sharpe")
            table.add_column("MaxDD")
            table.add_column("PF")
            table.add_column("SQN")
            table.add_column("Recov")
            table.add_column("P-Value")
            for b in report.benchmarks.comparisons:
                table.add_row(
                    b.name,
                    b.total_return,
                    f"[{self._get_color_for_metric(b.sharpe, 'sharpe')}]{b.sharpe}[/]",
                    b.max_drawdown,
                    f"[{self._get_color_for_metric(b.profit_factor, 'pf')}]{b.profit_factor}[/]",
                    b.sqn,
                    f"[{self._get_color_for_metric(b.recovery_factor, 'recovery')}]{b.recovery_factor}[/]",
                    b.p_value,
                )
            self.console.print(table)

        if report.rl_evaluation:
            self.console.print(f"\n[bold magenta]{section_idx}. RL Agent Evaluation[/]")
            section_idx += 1
            self.console.print(f"Summary: {report.rl_evaluation.comparison_summary}")
            table = Table(box=None)
            table.add_column("Agent")
            table.add_column("Sharpe")
            table.add_column("Sortino")
            table.add_column("PF")
            table.add_column("MaxDD")
            table.add_column("VaR(95)")
            table.add_column("SQN")
            for m in report.rl_evaluation.metrics:
                table.add_row(
                    m.agent_name,
                    f"[{self._get_color_for_metric(m.sharpe, 'sharpe')}]{m.sharpe:.2f}[/]",
                    f"{m.sortino:.2f}",
                    f"[{self._get_color_for_metric(m.profit_factor, 'pf')}]{m.profit_factor:.2f}[/]",
                    f"{m.max_dd:.2%}",
                    f"{m.var_95:.2%}",
                    f"{m.sqn:.2f}",
                )
            self.console.print(table)

        if report.rare_events:
            self.console.print(f"\n[bold red]{section_idx}. Rare Event Simulations[/]")
            section_idx += 1
            table = Table(box=None)
            table.add_column("Event Type")
            table.add_column("Impact")
            table.add_column("Recovery")
            for s in report.rare_events.scenarios:
                table.add_row(
                    s.event_type, f"{s.peak_impact_pct:.2%}", f"{s.recovery_attained:.1%}"
                )
            self.console.print(table)

        if report.calibration_analysis:
            self.console.print(f"\n[bold cyan]{section_idx}. Confidence Calibration & Reliability[/]")
            section_idx += 1
            self.console.print(
                f"ECE: [bold]{report.calibration_analysis.ece:.4f}[/] | "
                f"Brier Score: [bold]{report.calibration_analysis.brier_score:.4f}[/] | "
                f"Status: [bold]{report.calibration_analysis.status}[/]"
            )
            table = Table(box=None)
            table.add_column("Confidence Range")
            table.add_column("Accuracy")
            table.add_column("Avg Confidence")
            table.add_column("Samples")
            for b in report.calibration_analysis.buckets:
                table.add_row(
                    b.range, f"{b.accuracy:.1%}", f"{b.confidence:.1%}", str(b.samples)
                )
            self.console.print(table)
            self.console.print(f"[dim]Insight: {report.calibration_analysis.reliability_insight}[/]")

        if report.execution_quality:
            self.console.print(f"\n[bold blue]{section_idx}. Execution Quality & Alpha Decay[/]")
            section_idx += 1
            self.console.print(
                f"Efficiency Score: [bold]{report.execution_quality.efficiency_score:.1f}/100[/]"
            )
            self.console.print(
                f"Opportunity Cost (Blocked): [bold red]{report.execution_quality.opportunity_cost}[/]"
            )
            table = Table(box=None)
            table.add_column("Metric")
            table.add_column("Value")
            table.add_column("Status")
            for m in report.execution_quality.metrics:
                table.add_row(m.name, m.value, m.status)
            self.console.print(table)

        self.console.print("\n[bold]Conclusion[/]")
        self.console.print(report.conclusion)

        if report.recommendations:
            self.console.print("\n[bold]Recommendations[/]")
            for rec in report.recommendations:
                self.console.print(f"- {rec}")

        self.console.print("\n" + "=" * 50 + "\n")


class ResearchOrchestrator:
    """
    Automates the aggregation of research results into a unified report.
    """

    def __init__(
        self,
        title: str,
        executive_summary: str,
        conclusion: str,
        overall_status: str = "PROVISIONAL",
        recommendations: list[str] | None = None,
    ):
        self.report = ResearchReport(
            title=title,
            executive_summary=executive_summary,
            conclusion=conclusion,
            overall_status=overall_status,
            recommendations=recommendations or [],
        )

    def add_section(self, section: BaseModel) -> None:
        """Add a section to the report based on its type."""
        if isinstance(section, RegimeSection):
            self.report.regime_analysis = section
        elif isinstance(section, StressTestSection):
            self.report.stress_tests = section
        elif isinstance(section, HyperparameterSection):
            self.report.hyperparameter_robustness = section
        elif isinstance(section, TradePatternSection):
            self.report.trade_patterns = section
        elif isinstance(section, ModelDriftSection):
            self.report.model_drift = section
        elif isinstance(section, AllocationSection):
            self.report.allocation_insights = section
        elif isinstance(section, BenchmarkSection):
            self.report.benchmarks = section
        elif isinstance(section, RLSection):
            self.report.rl_evaluation = section
        elif isinstance(section, RareEventSection):
            self.report.rare_events = section
        elif isinstance(section, CalibrationSection):
            self.report.calibration_analysis = section
        elif isinstance(section, ExecutionQualitySection):
            self.report.execution_quality = section
        else:
            raise ValueError(f"Unknown section type: {type(section)}")

    def set_status(self, status: str) -> None:
        """Set the overall status of the report."""
        self.report.overall_status = status

    def add_recommendation(self, recommendation: str) -> None:
        """Add a single recommendation to the report."""
        self.report.recommendations.append(recommendation)

    def build(self) -> ResearchReport:
        """Return the finalized report."""
        return self.report

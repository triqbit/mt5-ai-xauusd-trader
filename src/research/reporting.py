"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Automated research summary generation for institutional review.

Author : Jules (sagsgrok)
License: MIT
"""

from __future__ import annotations

import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# --- Models ---

class RegimeAnalysis(BaseModel):
    """Analysis of market regimes detected during the period."""
    current_regime: str
    regime_distribution: Dict[str, float]  # Regime Name -> Percentage of time
    volatility_profile: str
    regime_shift_detected: bool = False
    details: Optional[str] = None


class StressTestOutcome(BaseModel):
    """Results from scenario-based stress testing."""
    scenario_name: str
    max_drawdown: float
    recovery_period_bars: int
    pnl_impact: float
    passed: bool
    fail_reason: Optional[str] = None


class HyperparameterRobustness(BaseModel):
    """Insight into parameter stability across walk-forward windows."""
    parameter_name: str
    optimal_value: Any
    stability_score: float = Field(..., ge=0.0, le=1.0)
    sensitivity_to_noise: str  # Low, Medium, High
    recommendation: str


class TradePatternFindings(BaseModel):
    """Patterns identified in trade journals (e.g., via JournalMiner)."""
    pattern_name: str
    frequency: int
    win_rate_impact: float
    significance_score: float
    description: str


class ModelDriftObservation(BaseModel):
    """Observations regarding concept drift or performance degradation."""
    model_id: str
    metric_name: str
    baseline_value: float
    current_value: float
    drift_detected: bool
    drift_score: float


class AllocationInsight(BaseModel):
    """Insights into capital allocation efficiency."""
    strategy_id: str
    allocated_weight: float
    performance_contribution: float
    marginal_sharpe: float
    over_allocated: bool


class BenchmarkComparison(BaseModel):
    """Comparison against standard benchmarks."""
    benchmark_name: str
    strategy_return: float
    benchmark_return: float
    alpha: float
    beta: float
    tracking_error: float


class ResearchReport(BaseModel):
    """Unified structure for a high-quality research summary."""
    report_id: str
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(timezone.utc))
    period_start: datetime.date
    period_end: datetime.date
    summary: str

    regime_analysis: Optional[RegimeAnalysis] = None
    stress_tests: List[StressTestOutcome] = Field(default_factory=list)
    hyperparameter_robustness: List[HyperparameterRobustness] = Field(default_factory=list)
    trade_patterns: List[TradePatternFindings] = Field(default_factory=list)
    model_drift: List[ModelDriftObservation] = Field(default_factory=list)
    allocation_insights: List[AllocationInsight] = Field(default_factory=list)
    benchmarks: List[BenchmarkComparison] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


# --- Reporter ---

class ResearchReporter:
    """Orchestrates the generation and formatting of research reports."""

    def __init__(self, template_dir: Optional[Path] = None):
        self.console = Console()
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate_markdown(self, report: ResearchReport, template_name: str = "research_report_template.md") -> str:
        """Renders the research report into a Markdown string using Jinja2."""
        template = self.jinja_env.get_template(template_name)
        return template.render(report.model_dump())

    def display_in_terminal(self, report: ResearchReport) -> None:
        """Displays a beautiful summary of the report in the terminal."""
        self.console.print(Panel(
            f"[bold blue]Research Report:[/bold blue] {report.report_id}\n"
            f"[dim]Period: {report.period_start} to {report.period_end}[/dim]",
            title="Institutional Research Summary",
            expand=False
        ))

        self.console.print(f"\n[bold]Executive Summary:[/bold]\n{report.summary}")

        if report.regime_analysis:
            ra = report.regime_analysis
            table = Table(title="Market Regime Analysis", title_style="bold magenta")
            table.add_column("Regime")
            table.add_column("Distribution (%)")
            table.add_column("Volatility")
            for k, v in ra.regime_distribution.items():
                row_style = "bold cyan" if k == ra.current_regime else ""
                table.add_row(k, f"{v*100:.1f}", ra.volatility_profile, style=row_style)
            self.console.print(table)

        if report.stress_tests:
            table = Table(title="Stress Test Outcomes", title_style="bold red")
            table.add_column("Scenario")
            table.add_column("Max DD", justify="right")
            table.add_column("PnL Impact", justify="right")
            table.add_column("Status", justify="center")
            for st in report.stress_tests:
                status = "[green]PASS[/green]" if st.passed else "[red]FAIL[/red]"
                table.add_row(st.scenario_name, f"{st.max_drawdown:.2%}", f"{st.pnl_impact:.2f}", status)
            self.console.print(table)

        if report.hyperparameter_robustness:
            table = Table(title="Hyperparameter Robustness", title_style="bold blue")
            table.add_column("Parameter")
            table.add_column("Optimal Value")
            table.add_column("Stability", justify="right")
            table.add_column("Noise Sens.")
            for hr in report.hyperparameter_robustness:
                table.add_row(hr.parameter_name, str(hr.optimal_value), f"{hr.stability_score:.2f}", hr.sensitivity_to_noise)
            self.console.print(table)

        if report.trade_patterns:
            self.console.print("\n[bold]Trade Pattern Findings:[/bold]")
            for tp in report.trade_patterns:
                self.console.print(f"• [cyan]{tp.pattern_name}[/cyan] (Freq: {tp.frequency}) | Impact: [green]{tp.win_rate_impact:+.2%}[/green]")

        if report.model_drift:
            table = Table(title="Model Health & Drift", title_style="bold yellow")
            table.add_column("Model ID")
            table.add_column("Metric")
            table.add_column("Current")
            table.add_column("Drift Score", justify="right")
            for md_obs in report.model_drift:
                color = "red" if md_obs.drift_detected else "green"
                table.add_row(md_obs.model_id, md_obs.metric_name, f"{md_obs.current_value:.4f}", f"[{color}]{md_obs.drift_score:.2f}[/{color}]")
            self.console.print(table)

        if report.allocation_insights:
            table = Table(title="Allocation Insights", title_style="bold green")
            table.add_column("Strategy")
            table.add_column("Weight", justify="right")
            table.add_column("Contribution", justify="right")
            table.add_column("Marginal Sharpe", justify="right")
            for ai in report.allocation_insights:
                color = "red" if ai.over_allocated else "white"
                table.add_row(ai.strategy_id, f"{ai.allocated_weight:.2%}", f"{ai.performance_contribution:.2%}", f"{ai.marginal_sharpe:.2f}", style=color)
            self.console.print(table)

        if report.benchmarks:
            table = Table(title="Benchmark Comparisons", title_style="bold white")
            table.add_column("Benchmark")
            table.add_column("Alpha", justify="right")
            table.add_column("Beta", justify="right")
            table.add_column("Strategy Ret.", justify="right")
            table.add_column("Benchmark Ret.", justify="right")
            for bc in report.benchmarks:
                table.add_row(bc.benchmark_name, f"{bc.alpha:.2f}", f"{bc.beta:.2f}", f"{bc.strategy_return:.2%}", f"{bc.benchmark_return:.2%}")
            self.console.print(table)

    def export_to_file(self, report: ResearchReport, output_dir: Path) -> Path:
        """Exports both JSON and Markdown versions of the report."""
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / f"{report.report_id}.json"
        md_path = output_dir / f"{report.report_id}.md"

        json_path.write_text(report.to_json())
        md_path.write_text(self.generate_markdown(report))

        return md_path

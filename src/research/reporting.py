"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/reporting.py
Institutional-grade research reporting system.
Author : triqbit
License: MIT
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
    regimes: List[RegimeSummary]
    transition_insights: str


class StressedMetric(BaseModel):
    name: str
    total_return: str
    max_drawdown: str
    sharpe: str
    outcome: str


class StressTestSection(BaseModel):
    resilience_score: float
    baseline: StressedMetric
    scenarios: List[StressedMetric]
    fragility_indicators: List[str]
    failure_points: List[str]


class ParameterRobustness(BaseModel):
    name: str
    range: str
    optimal: str
    sensitivity: str


class HyperparameterSection(BaseModel):
    stability_score: float
    parameters: List[ParameterRobustness]
    insights: str


class PatternConcentration(BaseModel):
    attribute: str
    value: str
    win_rate: float
    profit_factor: float


class BehavioralRisk(BaseModel):
    type: str
    description: str


class TradePatternSection(BaseModel):
    primary_insight: str
    concentrations: List[PatternConcentration]
    behavioral_risks: List[BehavioralRisk]


class DriftMetric(BaseModel):
    name: str
    baseline: str
    current: str
    drift_pct: float
    status: str


class ModelDriftSection(BaseModel):
    metrics: List[DriftMetric]
    feature_shifts: str


class AllocationEntry(BaseModel):
    name: str
    amount: str
    heat_pct: float
    multiplier: float


class AllocationSection(BaseModel):
    total_heat_pct: float
    allocations: List[AllocationEntry]
    rejection_summary: Dict[str, int]


class BenchmarkComparison(BaseModel):
    name: str
    total_return: str
    sharpe: str
    max_drawdown: str
    p_value: str


class BenchmarkSection(BaseModel):
    comparisons: List[BenchmarkComparison]
    statistical_summary: str


class RLMetric(BaseModel):
    agent_name: str
    sharpe: float
    profit_factor: float
    max_dd: float
    win_rate: float


class RLSection(BaseModel):
    comparison_summary: str
    best_agent: str
    performance_gap: float
    metrics: List[RLMetric]


# --- Full Report Model ---


class ResearchReport(BaseModel):
    """Structured research report container."""

    title: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    author: str = "Jules Research"
    executive_summary: str

    regime_analysis: Optional[RegimeSection] = None
    stress_tests: Optional[StressTestSection] = None
    hyperparameter_robustness: Optional[HyperparameterSection] = None
    trade_patterns: Optional[TradePatternSection] = None
    model_drift: Optional[ModelDriftSection] = None
    allocation_insights: Optional[AllocationSection] = None
    benchmarks: Optional[BenchmarkSection] = None
    rl_evaluation: Optional[RLSection] = None

    conclusion: str


class ResearchReporter:
    """
    Orchestrator for generating research reports.
    Supports terminal display (rich) and Markdown export (jinja2).
    """

    def __init__(self, template_dir: Optional[str] = None):
        if not template_dir:
            # Default to relative path from this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(base_dir, "templates")

        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.console = Console()

    def generate_markdown(self, report: ResearchReport) -> str:
        """Render the report as a Markdown string."""
        template = self.jinja_env.get_template("research_report.md.j2")
        return str(template.render(report.model_dump()))

    def save_markdown(self, report: ResearchReport, filepath: str) -> None:
        """Save the report to a Markdown file."""
        content = self.generate_markdown(report)
        with open(filepath, "w") as f:
            f.write(content)

    def generate_html(self, report: ResearchReport) -> str:
        """Render the report as an HTML string."""
        template = self.jinja_env.get_template("research_report.html.j2")
        return str(template.render(report.model_dump()))

    def save_html(self, report: ResearchReport, filepath: str) -> None:
        """Save the report to an HTML file."""
        content = self.generate_html(report)
        with open(filepath, "w") as f:
            f.write(content)

    def format_for_terminal(self, report: ResearchReport) -> None:
        """Print a scannable version of the report to the terminal."""
        self.console.print(
            Panel(
                f"[bold blue]{report.title}[/]\n[dim]Date: {report.timestamp} | Author: {report.author}[/]"
            )
        )

        self.console.print("\n[bold]Executive Summary[/]")
        self.console.print(report.executive_summary)

        if report.regime_analysis:
            self.console.print("\n[bold cyan]1. Market Regime Analysis[/]")
            table = Table(box=None)
            table.add_column("Regime")
            table.add_column("Frequency")
            table.add_column("Profitability")
            for r in report.regime_analysis.regimes:
                table.add_row(r.label, f"{r.frequency_pct}%", r.profitability)
            self.console.print(table)

        if report.stress_tests:
            self.console.print("\n[bold red]2. Stress Test Outcomes[/]")
            self.console.print(
                f"Resilience Score: [bold]{report.stress_tests.resilience_score}/100[/]"
            )
            table = Table(box=None)
            table.add_column("Scenario")
            table.add_column("Return")
            table.add_column("MaxDD")
            table.add_column("Outcome")
            table.add_row(
                "Baseline",
                report.stress_tests.baseline.total_return,
                report.stress_tests.baseline.max_drawdown,
                "N/A",
            )
            for s in report.stress_tests.scenarios:
                table.add_row(s.name, s.total_return, s.max_drawdown, s.outcome)
            self.console.print(table)

        if report.hyperparameter_robustness:
            self.console.print("\n[bold magenta]3. Hyperparameter Robustness[/]")
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
            self.console.print("\n[bold yellow]4. Trade Pattern Findings[/]")
            self.console.print(f"Insight: {report.trade_patterns.primary_insight}")
            table = Table(box=None)
            table.add_column("Attribute")
            table.add_column("Value")
            table.add_column("PF")
            for c in report.trade_patterns.concentrations:
                table.add_row(c.attribute, c.value, f"{c.profit_factor:.2f}")
            self.console.print(table)

        if report.model_drift:
            self.console.print("\n[bold blue]5. Model Drift Observations[/]")
            table = Table(box=None)
            table.add_column("Metric")
            table.add_column("Drift %")
            table.add_column("Status")
            for m in report.model_drift.metrics:
                table.add_row(m.name, f"{m.drift_pct}%", m.status)
            self.console.print(table)

        if report.allocation_insights:
            self.console.print("\n[bold green]6. Capital Allocation[/]")
            self.console.print(f"Total Heat: {report.allocation_insights.total_heat_pct}%")
            table = Table(box=None)
            table.add_column("Target")
            table.add_column("Amount")
            table.add_column("Heat")
            for a in report.allocation_insights.allocations:
                table.add_row(a.name, a.amount, f"{a.heat_pct}%")
            self.console.print(table)

        if report.benchmarks:
            self.console.print("\n[bold white]7. Benchmark Comparisons[/]")
            table = Table(box=None)
            table.add_column("Strategy")
            table.add_column("Return")
            table.add_column("Sharpe")
            table.add_column("P-Value")
            for b in report.benchmarks.comparisons:
                table.add_row(b.name, b.total_return, b.sharpe, b.p_value)
            self.console.print(table)

        if report.rl_evaluation:
            self.console.print("\n[bold magenta]8. RL Agent Evaluation[/]")
            self.console.print(f"Summary: {report.rl_evaluation.comparison_summary}")
            table = Table(box=None)
            table.add_column("Agent")
            table.add_column("Sharpe")
            table.add_column("PF")
            table.add_column("MaxDD")
            table.add_column("Win Rate")
            for m in report.rl_evaluation.metrics:
                table.add_row(
                    m.agent_name,
                    f"{m.sharpe:.2f}",
                    f"{m.profit_factor:.2f}",
                    f"{m.max_dd:.2%}",
                    f"{m.win_rate:.2%}",
                )
            self.console.print(table)

        self.console.print("\n[bold]Conclusion[/]")
        self.console.print(report.conclusion)
        self.console.print("\n" + "=" * 50 + "\n")

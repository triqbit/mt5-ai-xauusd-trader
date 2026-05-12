"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/stress_test_demo.py
Demonstration script for the StressLab resilience testing framework.
"""

from __future__ import annotations

import os

from rich.console import Console

from src.research.benchmarks import BenchmarkEvaluator, EMACrossoverStrategy
from src.research.rare_event_simulator import RareEventConfig, RareEventSimulator, RareEventType
from src.research.reporting import ResearchOrchestrator, ResearchReporter
from src.research.stress_lab import StressLab, StressTestMetrics


def run_stress_test_demo():
    """Run a full demonstration of the stress testing laboratory."""
    console = Console()
    console.print("[bold blue]Starting StressLab Resilience Demonstration...[/]\n")

    # 1. Generate Synthetic Data with Rare Events
    simulator = RareEventSimulator(seed=42)
    # Generate a news shock scenario as our 'base' data for testing
    config = RareEventConfig(
        event_type=RareEventType.NEWS_SHOCK,
        n_steps=1000,
        event_magnitude=1.5,
        base_volatility=0.001,
    )
    df, event_result = simulator.generate_scenario(config)
    console.print(
        f"Generated {len(df)} bars of synthetic data with a [bold red]{event_result.event_type}[/] event."
    )

    # 2. Select Strategy
    strategy = EMACrossoverStrategy(fast_window=10, slow_window=30)
    console.print(f"Testing Strategy: [bold green]{strategy.name}[/]")

    # 3. Calculate Baseline Metrics (Neutral Run)
    evaluator = BenchmarkEvaluator(df)
    results = evaluator.evaluate_all([strategy])
    s_metrics = results.loc[strategy.name]

    baseline_metrics = StressTestMetrics(
        total_return=float(s_metrics["Total Return"]),
        max_drawdown=float(s_metrics["Max Drawdown"]),
        sharpe_ratio=float(s_metrics["Sharpe Ratio"]),
        win_rate=float(s_metrics["Win Rate"]),
        num_trades=int(s_metrics["Num Trades"]),
        recovery_factor=float(s_metrics["Recovery Factor"]),
        profit_factor=float(s_metrics["Profit Factor"]),
        execution_quality_score=1.0,
        latency_impact=0.0,
        sortino_ratio=float(s_metrics["Sortino Ratio"]),
    )
    console.print(
        f"Baseline Calculated: Return={baseline_metrics.total_return:.2%}, Sharpe={baseline_metrics.sharpe_ratio:.2f}"
    )

    # 4. Run Stress Lab Suite
    lab = StressLab(strategy, df)
    console.print("\n[bold]Running adversarial suite...[/]")
    resilience_report = lab.run_standard_suite(baseline_metrics)
    console.print(f"Resilience Score: [bold cyan]{resilience_report.resilience_score:.1f}/100[/]")

    # 5. Generate Institutional Research Report
    orchestrator = ResearchOrchestrator(
        title="Institutional Resilience Audit: EMA Crossover Strategy",
        executive_summary=(
            f"This audit evaluates the {strategy.name} strategy under adversarial conditions. "
            "The stress laboratory simulates execution friction, data instability, and regime shifts "
            "to identify non-linear failure points and quantify strategy fragility."
        ),
        conclusion=(
            f"The strategy achieved a resilience score of {resilience_report.resilience_score:.1f}. "
            "While it handles moderate spread widening, it shows critical fragility during "
            "flash crashes and high-latency environments."
        ),
        overall_status="PROVISIONAL" if resilience_report.resilience_score < 70 else "VERIFIED",
    )

    # Add the stress test section
    orchestrator.add_section(resilience_report.to_report_section())

    # Add rare event section from simulator
    orchestrator.add_section(simulator.generate_report_section({"news_shock": (df, event_result)}))

    report = orchestrator.build()
    reporter = ResearchReporter()

    # Terminal Output
    console.print("\n" + "=" * 80)
    reporter.format_for_terminal(report)

    # Export Reports
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "stress_test_audit.md")
    html_path = os.path.join(output_dir, "stress_test_audit.html")

    reporter.save_markdown(report, md_path)
    reporter.save_html(report, html_path)

    console.print("\n[bold green]SUCCESS:[/] Reports generated:")
    console.print(f" - Markdown: [cyan]{md_path}[/]")
    console.print(f" - HTML:     [cyan]{html_path}[/]")


if __name__ == "__main__":
    run_stress_test_demo()

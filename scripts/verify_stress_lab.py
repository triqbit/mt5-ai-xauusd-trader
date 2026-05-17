"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/verify_stress_lab.py
Verification script for the StressLab framework.
"""

import os
import sys

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.research import EMACrossoverStrategy, StressLab


def generate_synthetic_data(n=1000):
    """Generate synthetic XAUUSD data."""
    np.random.seed(42)
    # Trend + Noise
    close = 2300 + np.cumsum(np.random.randn(n) * 2 + 0.1)
    df = pd.DataFrame(
        {
            "open": close - np.random.randn(n),
            "high": close + np.abs(np.random.randn(n) * 2),
            "low": close - np.abs(np.random.randn(n) * 2),
            "close": close,
            "tick_volume": np.random.randint(100, 1000, n),
            "spread": np.ones(n) * 0.25,
        }
    )
    df.index = pd.date_range(start="2024-01-01", periods=n, freq="5min")
    return df


def main():
    console = Console()
    console.print("[bold blue]🚀 Starting StressLab Framework Verification...[/]")

    # 1. Setup Data
    data = generate_synthetic_data(2000)
    strategy = EMACrossoverStrategy(9, 21)
    lab = StressLab(strategy, data)

    # 2. Get Baseline
    console.print("\n[bold]📈 Calculating Baseline Metrics...[/]")
    # We use a neutral scenario as baseline
    from src.research.stress_lab import StressScenario

    baseline_scenario = StressScenario(name="Baseline", description="No stress")
    baseline_metrics = lab.run_scenario(baseline_scenario)

    # 3. Run Standard Suite
    console.print("\n[bold]🧪 Running Standard Stress Suite...[/]")
    report = lab.run_standard_suite(baseline_metrics)

    # 4. Display Summary Table
    table = Table(title=f"Stress Test Report: {strategy.name}")
    table.add_column("Scenario", style="cyan")
    table.add_column("Return", justify="right")
    table.add_column("MaxDD", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Recovery Factor", justify="right")
    table.add_column("Slippage (Max)", justify="right")

    # Add Baseline
    table.add_row(
        "Baseline",
        f"{baseline_metrics.total_return:.2%}",
        f"{baseline_metrics.max_drawdown:.2%}",
        f"{baseline_metrics.sharpe_ratio:.2f}",
        f"{baseline_metrics.recovery_factor:.2f}",
        "N/A",
    )

    for name, m in report.scenario_results.items():
        if name == "Baseline":
            continue
        table.add_row(
            name,
            f"{m.total_return:.2%}",
            f"{m.max_drawdown:.2%}",
            f"{m.sharpe_ratio:.2f}",
            f"{m.recovery_factor:.2f}",
            f"{m.max_slippage_experienced:.1f} bps",
        )

    console.print(table)

    # 5. Resilience Score & Insights
    console.print(f"\n[bold]Resilience Score: {report.resilience_score:.1f}/100[/]")

    if report.fragility_indicators:
        console.print("\n[bold yellow]⚠️ Fragility Indicators:[/]")
        for fi in report.fragility_indicators:
            console.print(f" - {fi}")

    if report.failure_points:
        console.print("\n[bold red]❌ Failure Points:[/]")
        for fp in report.failure_points:
            console.print(f" - {fp}")

    console.print(f"\n[bold]Summary:[/]\n{report.degradation_summary}")

    console.print("\n[bold green]✅ StressLab Framework Verification Complete![/]")


if __name__ == "__main__":
    main()

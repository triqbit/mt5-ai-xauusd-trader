"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/verify_benchmarking.py
Verification script for the benchmarking framework.
"""

import os
import sys

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.research import (
    BenchmarkEvaluator,
    EMACrossoverStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NaiveDirectionalStrategy,
    RandomStrategy,
    RiskFilteredBaseline,
    VolatilityBreakoutStrategy,
)


def generate_synthetic_data(n=1000):
    """Generate synthetic XAUUSD data."""
    np.random.seed(42)
    # Trend + Noise
    close = 2000 + np.cumsum(np.random.randn(n) * 2 + 0.1)
    df = pd.DataFrame(
        {
            "open": close - np.random.randn(n),
            "high": close + np.abs(np.random.randn(n) * 2),
            "low": close - np.abs(np.random.randn(n) * 2),
            "close": close,
            "tick_volume": np.random.randint(100, 1000, n),
        }
    )
    df.index = pd.date_range(start="2024-01-01", periods=n, freq="5min")
    return df


def main():
    console = Console()
    console.print("[bold blue]🚀 Starting Benchmarking Framework Verification...[/]")

    # 1. Setup Data
    data = generate_synthetic_data(1000)
    evaluator = BenchmarkEvaluator(data, initial_balance=10000.0, commission=0.0001)

    # 2. Define Strategies
    strategies = [
        EMACrossoverStrategy(9, 21),
        MomentumStrategy(14),
        VolatilityBreakoutStrategy(20, 2.0),
        NaiveDirectionalStrategy(),
        RiskFilteredBaseline(9, 21, 0.01),
        MeanReversionStrategy(14, 70, 30),
        RandomStrategy(seed=42),
    ]

    # 3. Evaluate All
    console.print("\n[bold]📊 Running Evaluations...[/]")
    summary_df = evaluator.evaluate_all(strategies)

    table = Table(title="Strategy Performance Summary")
    table.add_column("Strategy", style="cyan")
    table.add_column("Return", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("MaxDD", justify="right")
    table.add_column("Trades", justify="right")

    for name, row in summary_df.iterrows():
        table.add_row(
            str(name),
            f"{row['Total Return']:.2%}",
            f"{row['Sharpe Ratio']:.2f}",
            f"{row['Max Drawdown']:.2%}",
            f"{int(row['Num Trades'])}",
        )
    console.print(table)

    # 4. Statistical Comparison
    baseline_name = f"Random_Baseline_seed_{42}"
    console.print(f"\n[bold]🧪 Comparing strategies against {baseline_name}...[/]")

    comp_table = Table(title=f"Statistical Comparison (vs {baseline_name})")
    comp_table.add_column("Strategy", style="cyan")
    comp_table.add_column("Outperformance", justify="right")
    comp_table.add_column("T-Stat", justify="right")
    comp_table.add_column("P-Value", justify="right")
    comp_table.add_column("Significant", justify="center")

    for strategy in strategies:
        if strategy.name == baseline_name:
            continue

        comp = evaluator.compare_to_baseline(strategy.name, baseline_name)

        is_sig = comp.get("Significant", False)
        sig_str = "[green]YES[/]" if is_sig else "[red]NO[/]"

        comp_table.add_row(
            strategy.name,
            f"{comp['Outperformance']:.2%}",
            f"{comp['T-Statistic']:.4f}",
            f"{comp['P-Value']:.4f}",
            sig_str,
        )

    console.print(comp_table)

    console.print("\n[bold green]✅ Benchmarking Framework Verification Complete![/]")


if __name__ == "__main__":
    main()

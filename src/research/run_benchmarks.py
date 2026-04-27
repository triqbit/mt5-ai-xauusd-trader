"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/run_benchmarks.py
Demonstration script to run and compare baseline strategies.
"""

import numpy as np
from rich.console import Console
from rich.table import Table

from src.environment.gym_env import TradingEnv
from src.research.benchmarks import (
    BenchmarkEvaluator,
    EMACrossoverBaseline,
    MomentumBaseline,
    NaiveDirectionalBaseline,
    RiskFilteredBaseline,
    VolatilityBreakoutBaseline,
    generate_comparison_table,
)


def create_synthetic_data(n_steps=1000):
    """Generate synthetic trending and mean-reverting data."""
    np.random.seed(42)

    # Simple random walk with a bit of drift
    returns = np.random.normal(0.0001, 0.01, n_steps)
    price = 2000.0 * np.exp(np.cumsum(returns))

    # OHLCV
    data = np.zeros((n_steps, 5))
    data[:, 3] = price # Close
    data[:, 0] = price * (1 + np.random.normal(0, 0.001, n_steps)) # Open
    data[:, 1] = np.maximum(data[:, 0], data[:, 3]) * (1 + np.random.uniform(0, 0.002, n_steps)) # High
    data[:, 2] = np.minimum(data[:, 0], data[:, 3]) * (1 - np.random.uniform(0, 0.002, n_steps)) # Low
    data[:, 4] = np.random.randint(100, 1000, n_steps) # Volume

    return data

def main():
    console = Console()
    console.print("[bold blue]MT5 Strategy Benchmarking Suite[/bold blue]")

    # 1. Setup environment
    data = create_synthetic_data(2000)
    env = TradingEnv(data, window_size=60)
    evaluator = BenchmarkEvaluator(env)

    # 2. Define strategies
    strategies = [
        EMACrossoverBaseline(window_size=60),
        MomentumBaseline(window_size=60),
        VolatilityBreakoutBaseline(window_size=60),
        NaiveDirectionalBaseline(window_size=60),
    ]

    # Add a risk-filtered version of the best-performing simple one (often momentum or breakout)
    strategies.append(RiskFilteredBaseline(VolatilityBreakoutBaseline(window_size=60), min_volatility=0.5))

    # 3. Run evaluation
    reports = []
    with console.status("[bold green]Evaluating strategies..."):
        for strategy in strategies:
            console.print(f"  Running [cyan]{strategy.name}[/cyan]...")
            report = evaluator.evaluate(strategy, n_episodes=10)
            reports.append(report)

    # 4. Display results
    df = generate_comparison_table(reports)

    table = Table(title="Strategy Comparison Report")
    table.add_column("Strategy", style="cyan")
    table.add_column("Cum. Return", justify="right")
    table.add_column("Sharpe Ratio", justify="right")
    table.add_column("Max Drawdown", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Total Trades", justify="right")

    for _, row in df.iterrows():
        table.add_row(
            row["strategy_name"],
            f"{row['cumulative_return']:.2%}",
            f"{row['sharpe_ratio']:.2f}",
            f"{row['max_drawdown']:.2%}",
            f"{row['win_rate']:.2%}",
            str(int(row["total_trades"]))
        )

    console.print(table)

if __name__ == "__main__":
    main()

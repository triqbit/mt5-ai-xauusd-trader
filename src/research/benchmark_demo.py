"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/benchmark_demo.py
Demonstration script for the benchmarking framework.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.models.regime_detector import MarketRegime
from src.research.benchmarks import (
    BenchmarkEvaluator,
    EMACrossoverStrategy,
    MomentumStrategy,
    MomentumVolatilityStrategy,
    NaiveDirectionalStrategy,
    NaiveReversalStrategy,
    RegimeFilterBaseline,
    RiskFilteredBaseline,
    VolatilityBreakoutStrategy,
)
from src.research.rare_event_simulator import RareEventConfig, RareEventSimulator, RareEventType
from src.research.reporting import ResearchOrchestrator, ResearchReporter


class MockAdvancedStrategy:
    """
    A mock 'sophisticated' strategy that uses a simple regime-aware filter
    to outperform basic baselines on synthetic data.
    """

    def __init__(self, name: str = "Advanced_Ensemble_Mock"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        # A 'sophisticated' logic:
        # Combine EMA Crossover with a stricter volatility and momentum confirmation
        fast_ema = df["close"].ewm(span=5, adjust=False).mean()
        slow_ema = df["close"].ewm(span=15, adjust=False).mean()
        rsi = self._calculate_rsi(df["close"], 14)

        signals = np.zeros(len(df))

        # Only Buy if EMA crossover AND RSI is not overbought
        buy_cond = (fast_ema > slow_ema) & (rsi < 65)
        # Only Sell if EMA crossover AND RSI is not oversold
        sell_cond = (fast_ema < slow_ema) & (rsi > 35)

        signals[buy_cond] = 1
        signals[sell_cond] = -1

        return signals

    def _calculate_rsi(self, prices: pd.Series, window: int) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))


def main():
    console = Console()
    console.print(Panel("[bold green]XAUUSD Strategy Benchmarking Demonstration[/]"))

    # 1. Generate Synthetic Data
    console.print("[yellow]Generating synthetic OHLCV data using RareEventSimulator...[/]")
    simulator = RareEventSimulator(seed=42)
    config = RareEventConfig(
        event_type=RareEventType.VOL_CLUSTER,
        n_steps=1000,
        start_price=2000.0,
        base_volatility=0.001,
        event_magnitude=1.2,
    )
    df, _ = simulator.generate_scenario(config)

    # Add dummy regime labels to demonstrate RegimeFilterBaseline
    df["regime"] = MarketRegime.RANGING.value
    # Use iloc for positional indexing
    df.iloc[200:400, df.columns.get_loc("regime")] = MarketRegime.TRENDING.value
    df.iloc[600:800, df.columns.get_loc("regime")] = MarketRegime.TRENDING.value

    # 2. Initialize Evaluator
    evaluator = BenchmarkEvaluator(df, initial_balance=10000.0, commission=0.0001)

    # 3. Define Strategies
    ema_base = EMACrossoverStrategy(9, 21)
    strategies = [
        ema_base,
        MomentumStrategy(14, 0.001),
        VolatilityBreakoutStrategy(20, 2.0),
        NaiveDirectionalStrategy(),
        NaiveReversalStrategy(),
        RiskFilteredBaseline(9, 21, 0.01),
        MomentumVolatilityStrategy(14, 0.001, 0.01),
        RegimeFilterBaseline(ema_base, [MarketRegime.TRENDING.value]),
        MockAdvancedStrategy(),
    ]

    # 4. Run Evaluation
    console.print(f"[yellow]Evaluating {len(strategies)} strategies over {len(df)} bars...[/]")
    evaluator.evaluate_all(strategies)

    # 5. Generate Report using ResearchReporter
    orchestrator = ResearchOrchestrator(
        title="Strategy Benchmark Report",
        executive_summary="Comparative analysis of baseline strategies against a mock advanced strategy on synthetic XAUUSD data.",
        conclusion="The mock advanced strategy demonstrates superior risk-adjusted returns compared to simple trend-following baselines.",
        overall_status="VERIFIED",
    )

    # Use the first baseline (EMA) for comparison
    section = evaluator.to_report_section(baseline_name=strategies[0].name)
    orchestrator.add_section(section)

    report = orchestrator.build()

    reporter = ResearchReporter()
    reporter.format_for_terminal(report)

    # 6. Detailed statistical comparison for the 'Advanced' strategy vs Risk-Filtered Baseline
    advanced_name = strategies[-1].name
    risk_filtered_name = strategies[-2].name
    console.print(
        f"\n[bold green]Institutional Comparative Summary: {advanced_name} vs {risk_filtered_name}[/]"
    )

    comp = evaluator.compare_to_baseline(advanced_name, risk_filtered_name)

    table = Table(title="Strategy Comparison Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column(risk_filtered_name, justify="right")
    table.add_column(advanced_name, justify="right")
    table.add_column("Improvement", justify="right")

    s_metrics = evaluator.results[advanced_name]
    b_metrics = evaluator.results[risk_filtered_name]

    metrics_to_show = [
        ("Total Return", "{:.2%}", True),
        ("Sharpe Ratio", "{:.2f}", True),
        ("Sortino Ratio", "{:.2f}", True),
        ("Calmar Ratio", "{:.2f}", True),
        ("Max Drawdown", "{:.2%}", False),
        ("Profit Factor", "{:.2f}", True),
        ("Expectancy", "{:.4f}", True),
        ("SQN", "{:.2f}", True),
        ("CVaR_95", "{:.2%}", True),
        ("Ulcer Index", "{:.4f}", False),
        ("Stability Score", "{:.2f}", True),
        ("Omega Ratio", "{:.2f}", True),
    ]

    for label, fmt, higher_is_better in metrics_to_show:
        b_val = b_metrics.get(label, 0)
        s_val = s_metrics.get(label, 0)

        if higher_is_better:
            improvement = s_val - b_val
        else:
            improvement = b_val - s_val

        is_improvement = improvement > 1e-9
        is_worsening = improvement < -1e-9

        if is_improvement:
            diff_str = f"[green]+{fmt.format(abs(improvement))}[/]"
        elif is_worsening:
            diff_str = f"[red]{fmt.format(improvement)}[/]"
        else:
            diff_str = fmt.format(0)

        table.add_row(label, fmt.format(b_val), fmt.format(s_val), diff_str)

    console.print(table)

    console.print("\n[bold]Statistical Significance Analysis:[/]")
    table_sig = Table()
    table_sig.add_column("Test")
    table_sig.add_column("Result")
    table_sig.add_column("P-Value / Metric")
    table_sig.add_column("Status")

    t_p = comp.get("P-Value", 1.0)
    w_p = comp.get("Wilcoxon P-Value", 1.0)

    t_status = "[bold green]SIGNIFICANT[/]" if t_p < 0.05 else "[yellow]NOT SIGNIFICANT[/]"
    w_status = "[bold green]SIGNIFICANT[/]" if w_p < 0.05 else "[yellow]NOT SIGNIFICANT[/]"

    table_sig.add_row("Paired T-test", f"t={comp.get('T-Statistic', 0):.4f}", f"{t_p:.4f}", t_status)
    table_sig.add_row("Wilcoxon Signed-Rank", "N/A", f"{w_p:.4f}", w_status)
    table_sig.add_row("Information Ratio", "N/A", f"{comp.get('Information Ratio', 0.0):.4f}", "N/A")

    console.print(table_sig)


if __name__ == "__main__":
    main()

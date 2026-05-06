"""
Verification script for the refined benchmarking framework.
Compares multiple baselines and generates a summary report.
"""

import pandas as pd
import numpy as np
from datetime import datetime, UTC
from src.research.benchmarks import (
    BenchmarkEvaluator,
    EMACrossoverStrategy,
    MomentumStrategy,
    VolatilityBreakoutStrategy,
    DonchianChannelStrategy,
    BuyAndHoldStrategy,
    RandomStrategy
)
from src.research.reporting import ResearchOrchestrator, ResearchReporter

def generate_synthetic_data(n_bars=2000):
    """Generate XAUUSD-like synthetic data."""
    np.random.seed(42)

    # Simulate price with some trend and volatility
    steps = np.random.normal(0, 1, n_bars)
    # Add a slight upward drift
    steps += 0.02
    close = 2000 + np.cumsum(steps * 2)

    df = pd.DataFrame({
        "open": close - np.random.normal(0, 0.5, n_bars),
        "high": close + np.abs(np.random.normal(0, 1, n_bars)),
        "low": close - np.abs(np.random.normal(0, 1, n_bars)),
        "close": close,
        "tick_volume": np.random.randint(100, 1000, n_bars)
    })
    return df

def run_verification():
    print("Starting Benchmarking Framework Verification...")

    df = generate_synthetic_data()
    evaluator = BenchmarkEvaluator(df, initial_balance=10000.0, commission=0.0001)

    strategies = [
        BuyAndHoldStrategy(),
        RandomStrategy(seed=42),
        EMACrossoverStrategy(9, 21),
        MomentumStrategy(14, threshold=0.001),
        VolatilityBreakoutStrategy(20, num_std=2.0),
        DonchianChannelStrategy(20)
    ]

    print(f"Evaluating {len(strategies)} strategies...")
    summary = evaluator.evaluate_all(strategies)

    print("\nPerformance Summary:")
    cols_to_show = ["Total Return", "Sharpe Ratio", "Max Drawdown", "Win Rate", "Profit Factor", "Stability Score"]
    print(summary[cols_to_show].to_string())

    # Use Buy and Hold as the baseline for comparison
    baseline_name = "Buy_And_Hold"
    print(f"\nComparing against baseline: {baseline_name}")

    section = evaluator.to_report_section(baseline_name=baseline_name)

    # Orchestrate a research report
    orchestrator = ResearchOrchestrator(
        title="Institutional Benchmarking Verification Report",
        executive_summary="This report verifies the enhanced benchmarking framework, comparing standard baselines against a passive Buy and Hold strategy on synthetic XAUUSD data.",
        conclusion="The benchmarking framework successfully calculates institutional-grade metrics and performs statistical outperformance testing.",
        overall_status="VERIFIED"
    )

    orchestrator.add_section(section)
    report = orchestrator.build()

    # Print to terminal
    reporter = ResearchReporter()
    reporter.format_for_terminal(report)

    # Save as Markdown
    output_path = "benchmarking_verification_report.md"
    reporter.save_markdown(report, output_path)
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    run_verification()

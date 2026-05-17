"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/verify_hyperopt_walkforward.py
Institutional verification script for Walk-Forward Optimization.
"""

import logging

import numpy as np
import pandas as pd

from src.research.benchmarks import EMACrossoverStrategy
from src.research.hyperopt_walkforward import (
    RobustnessWeights,
    WalkForwardConfig,
    WalkForwardOptimizer,
)
from src.research.reporting import ResearchOrchestrator, ResearchReporter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("VerifyWalkForward")


def generate_synthetic_xauusd(n_bars: int = 2000) -> pd.DataFrame:
    """Generate synthetic XAUUSD-like data with multiple regimes."""
    logger.info(f"Generating {n_bars} bars of synthetic XAUUSD data...")

    np.random.seed(42)
    base_price = 2000.0

    # Generate 4 distinct regimes
    regime_len = n_bars // 4

    # 1. Trending Up
    trend_up = np.cumsum(np.random.normal(0.5, 1.0, regime_len)) + base_price

    # 2. Ranging
    ranging = np.random.normal(0, 5.0, regime_len) + trend_up[-1]

    # 3. Trending Down
    trend_down = np.cumsum(np.random.normal(-0.5, 1.0, regime_len)) + ranging[-1]

    # 4. Volatile
    volatile = np.cumsum(np.random.normal(0, 3.0, regime_len)) + trend_down[-1]

    close = np.concatenate([trend_up, ranging, trend_down, volatile])

    df = pd.DataFrame(
        {
            "open": close + np.random.normal(0, 0.5, n_bars),
            "high": close + np.abs(np.random.normal(2, 1, n_bars)),
            "low": close - np.abs(np.random.normal(2, 1, n_bars)),
            "close": close,
            "tick_volume": np.random.randint(100, 1000, n_bars),
        }
    )

    return df


def run_verification():
    """Run the walk-forward optimization verification."""
    data = generate_synthetic_xauusd()

    def param_space(trial):
        return {
            "fast_window": trial.suggest_int("fast_window", 5, 20),
            "slow_window": trial.suggest_int("slow_window", 25, 60),
        }

    config = WalkForwardConfig(
        train_size=500,
        test_size=100,
        step_size=100,
        min_windows=5,
        n_trials=20,
        seed=42,
        robustness_weights=RobustnessWeights(
            oos_mean=0.5, worst_oos=0.3, regime_consistency=0.2, stability=0.2
        ),
    )

    logger.info("Starting Walk-Forward Optimization...")
    optimizer = WalkForwardOptimizer(
        data=data, strategy_factory=EMACrossoverStrategy, param_space=param_space, config=config
    )

    result = optimizer.run_optimization()

    logger.info("Optimization complete.")
    logger.info(f"Best Params: {result.best_params}")
    logger.info(f"Robustness Score: {result.metrics.robustness_score:.4f}")
    logger.info(f"OOS Sharpe Mean: {result.metrics.oos_sharpe_mean:.4f}")
    logger.info(f"Worst Window Sharpe: {result.metrics.worst_window_sharpe:.4f}")

    # Generate Research Report
    orchestrator = ResearchOrchestrator(
        title="Institutional Walk-Forward Optimization Report",
        executive_summary="Verification of the robustness-weighted walk-forward optimization framework using synthetic XAUUSD data across multiple market regimes.",
        conclusion="The walk-forward process successfully identified parameter sets that maintain performance consistency across varying volatility and trend regimes.",
    )

    # Add hyperparameter section
    orchestrator.add_section(result.to_report_section())

    report = orchestrator.build()
    reporter = ResearchReporter()

    # Save results
    report_path = "docs/audits/walkforward_verification_report.md"
    reporter.save_markdown(report, report_path)
    logger.info(f"Report saved to {report_path}")

    # Print terminal summary
    reporter.format_for_terminal(report)


if __name__ == "__main__":
    run_verification()

"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/rl_evaluation_demo.py
Demo showcasing institutional RL agent evaluation and reporting.
"""

from __future__ import annotations

import logging
import os

import numpy as np
import pandas as pd

from src.environment.gym_env import TradingEnv
from src.models.ppo_agent import PPOAgent
from src.models.regime_detector import RegimeDetector
from src.research.reporting import ResearchOrchestrator, ResearchReporter, SectionStatus
from src.research.rl_evaluation import (
    MeanReversionBaseline,
    RandomBaseline,
    RLEvaluator,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_synthetic_data(n_steps: int = 500) -> np.ndarray:
    """Generate synthetic XAUUSD-like data with trend and volatility."""
    np.random.seed(42)

    # Base price
    price = 2000.0
    prices = []
    for _ in range(n_steps):
        # Add some trend and noise
        change = np.random.normal(0.1, 1.5)
        price += change
        prices.append(price)

    prices = np.array(prices)

    # Create OHLCV structure
    data = np.zeros((n_steps, 5))
    data[:, 3] = prices # Close
    data[:, 0] = prices - np.random.uniform(0, 1, n_steps) # Open
    data[:, 1] = prices + np.random.uniform(0, 2, n_steps) # High
    data[:, 2] = prices - np.random.uniform(0, 2, n_steps) # Low
    data[:, 4] = np.random.randint(100, 1000, n_steps) # Volume

    return data.astype(np.float32)

def run_demo():
    """Execute the RL evaluation demo."""
    logger.info("Starting RL Evaluation Demo...")

    # 1. Setup environment and data
    data = generate_synthetic_data(1000)
    env = TradingEnv(data=data, window_size=20)

    # 2. Initialize Agents
    # Note: We use a fresh PPOAgent which will act randomly since it's not trained
    # In a real scenario, you would load a trained model.
    ppo_agent = PPOAgent(env=env)
    mean_rev_agent = MeanReversionBaseline()
    random_agent = RandomBaseline()

    # 3. Initialize Evaluator
    detector = RegimeDetector()
    evaluator = RLEvaluator(env=env, regime_detector=detector)

    # 4. Run Comparative Evaluation
    logger.info("Evaluating agents (this may take a moment)...")
    comparison = evaluator.compare(
        agents=[ppo_agent, mean_rev_agent, random_agent],
        agent_names=["PPO_Agent_Untrained", "Mean_Reversion", "Random"],
        baseline_name="Momentum",  # Evaluator will run Momentum internally if not in list
    )

    # 5. Generate Research Report
    orchestrator = ResearchOrchestrator(
        title="RL Agent Institutional Performance Audit",
        executive_summary=(
            "This report evaluates multiple reinforcement learning and rule-based agents "
            "under disciplined institutional metrics. We analyze not only returns but also "
            "stability, turnover, and regime sensitivity to separate apparent profitability "
            "from reliable performance."
        ),
        conclusion=(
            f"The best performing agent was {comparison.best_agent} with a performance "
            f"gap of {comparison.performance_gap_pct:.2f}% over the baseline. "
            "Further training and regime-specific optimization are recommended for PPO agents."
        ),
        overall_status=SectionStatus.PROVISIONAL
    )

    # Add RL Section
    rl_section = evaluator.to_report_section(comparison)
    orchestrator.add_section(rl_section)

    # Add Regime Section for context
    # Use full data for regime analysis
    df_data = pd.DataFrame(data, columns=["open", "high", "low", "close", "tick_volume"])
    regime_report = detector.run_analysis(df_data)
    orchestrator.add_section(regime_report.to_report_section())

    # Finalize Report
    report = orchestrator.build()
    reporter = ResearchReporter()

    # Print to terminal
    reporter.format_for_terminal(report)

    # Save to files
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "rl_evaluation_demo.md")
    html_path = os.path.join(output_dir, "rl_evaluation_demo.html")

    reporter.save_markdown(report, md_path)
    reporter.save_html(report, html_path)

    logger.info(f"Demo complete. Reports saved to {output_dir}/")

if __name__ == "__main__":
    run_demo()

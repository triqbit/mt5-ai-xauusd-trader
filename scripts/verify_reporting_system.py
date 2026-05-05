"""
Verification script for the MT5 AI Trading Bot Research Reporting System.
Generates a comprehensive "Gold Standard" research report using synthetic data.
"""

import os
from datetime import datetime, UTC
import numpy as np
import pandas as pd

from src.research.reporting import (
    ResearchOrchestrator,
    ResearchReporter,
    RegimeSection,
    RegimeSummary,
    StressTestSection,
    StressedMetric,
    HyperparameterSection,
    ParameterRobustness,
    TradePatternSection,
    PatternConcentration,
    BehavioralRisk,
    SignalMotif,
    ModelDriftSection,
    DriftMetric,
    AllocationSection,
    AllocationEntry,
    BenchmarkSection,
    BenchmarkComparison,
    RLSection,
    RLMetric,
    RareEventSection,
    RareEventSummary,
    ExecutionQualitySection,
    ExecutionMetric
)

def generate_gold_standard_report():
    print("Generating Gold Standard Research Report...")

    orchestrator = ResearchOrchestrator(
        title="Institutional Strategy Audit - Q1 2025",
        executive_summary=(
            "This report provides a comprehensive evaluation of the XAUUSD DeepRL-Ensemble strategy. "
            "The strategy demonstrates exceptional resilience in high-volatility regimes and maintains "
            "statistical significance over standard benchmarks. Optimization stability is high, though "
            "minor drift in the 'volatility' feature cluster warrants monitoring."
        ),
        conclusion=(
            "The strategy is cleared for production deployment with a 'VERIFIED' status. "
            "Performance remains robust across simulated tail-events and adversarial execution conditions."
        ),
        overall_status="VERIFIED",
        recommendations=[
            "Increase capital allocation to London session by 15%.",
            "Implement a drift-correction retrain if 'volatility' drift exceeds 0.25.",
            "Deploy with low-latency direct execution to maintain the 92% efficiency score."
        ]
    )

    # 1. Market Regimes
    orchestrator.add_section(RegimeSection(
        summary="Dominant regimes were Bullish Trend and High Volatility.",
        regimes=[
            RegimeSummary(label="Bullish Trend", frequency_pct=42.5, avg_duration_bars=120, profitability="High"),
            RegimeSummary(label="High Volatility", frequency_pct=28.0, avg_duration_bars=45, profitability="Moderate"),
            RegimeSummary(label="Mean Reverting", frequency_pct=19.5, avg_duration_bars=15, profitability="Low"),
            RegimeSummary(label="News Shock", frequency_pct=10.0, avg_duration_bars=5, profitability="Neutral")
        ],
        transition_insights="Transitions from Bullish Trend to News Shock were frequent but recovery was swift."
    ))

    # 2. Stress Tests
    orchestrator.add_section(StressTestSection(
        resilience_score=88.4,
        baseline=StressedMetric(name="Standard Market", total_return="18.2%", max_drawdown="5.1%", sharpe="2.4", outcome="PASS"),
        scenarios=[
            StressedMetric(name="Liquidity Vacuum", total_return="14.5%", max_drawdown="8.2%", sharpe="1.9", outcome="PASS"),
            StressedMetric(name="Flash Crash (XAUUSD)", total_return="9.1%", max_drawdown="12.5%", sharpe="1.2", outcome="PASS"),
            StressedMetric(name="Execution Hell", total_return="11.2%", max_drawdown="6.4%", sharpe="1.6", outcome="PASS")
        ],
        fragility_indicators=["Sensitivity to spread widening > 5.0 pips"],
        failure_points=["None detected within testing bounds"]
    ))

    # 3. Hyperparameters
    orchestrator.add_section(HyperparameterSection(
        stability_score=92.1,
        parameters=[
            ParameterRobustness(name="Learning Rate", range="1e-5 to 1e-3", optimal="3e-4", sensitivity="Low"),
            ParameterRobustness(name="Lookback Window", range="30 to 120", optimal="60", sensitivity="Moderate"),
            ParameterRobustness(name="Ensemble Threshold", range="0.5 to 0.7", optimal="0.6", sensitivity="High")
        ],
        insights="The stability of the optimal lookback window suggests consistent alpha capture."
    ))

    # 4. Trade Patterns
    orchestrator.add_section(TradePatternSection(
        primary_insight="Strongest performance during London/NY overlap.",
        concentrations=[
            PatternConcentration(attribute="Session", value="London", win_rate=0.68, profit_factor=2.4),
            PatternConcentration(attribute="Volatility", value="Normal", win_rate=0.62, profit_factor=1.8)
        ],
        behavioral_risks=[
            BehavioralRisk(type="Minor Overtrading", description="Detected during Asian session consolidation.")
        ],
        motifs=[
            SignalMotif(algorithm="ppo", direction=1, volatility_bucket="Extreme", confidence_bucket="Low", frequency=4, win_rate=0.25)
        ]
    ))

    # 5. Model Drift
    orchestrator.add_section(ModelDriftSection(
        metrics=[
            DriftMetric(name="Feature: Volatility_14", baseline="0.12", current="0.16", drift_pct=15.0, status="WARNING"),
            DriftMetric(name="Feature: RSI_9", baseline="45.0", current="46.2", drift_pct=2.1, status="STABLE")
        ],
        feature_shifts="Volatility indicators are showing increased importance (+0.12 shift)."
    ))

    # 6. Allocation
    orchestrator.add_section(AllocationSection(
        total_heat_pct=35.5,
        allocations=[
            AllocationEntry(name="XAUUSD_Ensemble", amount="$35,500", heat_pct=35.5, multiplier=1.1)
        ],
        rejection_summary={"Daily Loss Limit": 0, "Concentration": 0},
        diversification_score=0.95
    ))

    # 7. Benchmarks
    orchestrator.add_section(BenchmarkSection(
        comparisons=[
            BenchmarkComparison(name="EMA Crossover", total_return="4.2%", sharpe="0.8", max_drawdown="12.1%", p_value="0.0012"),
            BenchmarkComparison(name="Buy & Hold (Gold)", total_return="8.5%", sharpe="1.1", max_drawdown="15.4%", p_value="0.0045")
        ],
        statistical_summary="Strategy significantly outperforms all baselines with 99% confidence."
    ))

    # 8. RL Evaluation
    orchestrator.add_section(RLSection(
        comparison_summary="PPO-Ensemble remains the most stable agent architecture.",
        best_agent="Ensemble_v2",
        performance_gap=24.5,
        metrics=[
            RLMetric(agent_name="Ensemble_v2", sharpe=2.4, profit_factor=1.9, max_dd=0.05, win_rate=0.58, recovery_factor=3.6, var_95=0.015, sqn=4.2),
            RLMetric(agent_name="Standard_PPO", sharpe=1.8, profit_factor=1.5, max_dd=0.08, win_rate=0.54, recovery_factor=2.4, var_95=0.022, sqn=2.8)
        ]
    ))

    # 9. Rare Events
    orchestrator.add_section(RareEventSection(
        scenarios=[
            RareEventSummary(event_type="Liquidity Vacuum", peak_impact_pct=-0.035, realized_volatility=0.08, recovery_attained=0.92),
            RareEventSummary(event_type="Gold Gap", peak_impact_pct=0.02, realized_volatility=0.05, recovery_attained=1.0)
        ],
        insights="Strategy uses adaptive spread-filters to survive liquidity vacuums without catastrophic losses."
    ))

    # 10. Execution Quality
    orchestrator.add_section(ExecutionQualitySection(
        efficiency_score=92.5,
        metrics=[
            ExecutionMetric(name="Avg Slippage", value="0.4 pips", status="OK"),
            ExecutionMetric(name="Avg Latency", value="120ms", status="OK"),
            ExecutionMetric(name="Fill Quality", value="94.2%", status="OK")
        ],
        opportunity_cost="$1,240.50",
        trade_count=150,
        rejected_count=12
    ))

    report = orchestrator.build()
    reporter = ResearchReporter()

    # Create reports directory
    os.makedirs("reports", exist_ok=True)

    md_path = "reports/gold_standard_report.md"
    html_path = "reports/gold_standard_report.html"

    reporter.save_markdown(report, md_path)
    reporter.save_html(report, html_path)

    print(f"Reports generated successfully:")
    print(f"  Markdown: {md_path}")
    print(f"  HTML: {html_path}")

    # Also print for terminal verification
    reporter.format_for_terminal(report)

if __name__ == "__main__":
    generate_gold_standard_report()

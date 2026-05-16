"""
MT5 AI/ML Trading Bot - Enterprise Edition
scripts/verify_reporting_system.py
'Gold Standard' verification script for the institutional research reporting system.
"""

import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.research.reporting import (
    AllocationEntry,
    AllocationSection,
    BehavioralRisk,
    BenchmarkComparison,
    BenchmarkSection,
    DriftMetric,
    ExecutionMetric,
    ExecutionQualitySection,
    HyperparameterSection,
    ModelDriftSection,
    ParameterRobustness,
    PatternConcentration,
    RareEventSection,
    RareEventSummary,
    RegimeSection,
    RegimeSummary,
    ResearchOrchestrator,
    ResearchReporter,
    RLMetric,
    RLSection,
    SignalMotif,
    StressedMetric,
    StressTestSection,
    TradePatternSection,
)


def main():
    print("🚀 Starting Gold Standard Reporting Verification...")

    # 1. Initialize Orchestrator
    orchestrator = ResearchOrchestrator(
        title="Institutional Strategy Gold Standard Audit - 2025",
        executive_summary=(
            "This report serves as the 'Gold Standard' validation for the MT5 AI/ML XAUUSD research pipeline. "
            "It integrates verified mock data across all 10 analytical domains to ensure reporting integrity, "
            "formatting consistency, and institutional quality."
        ),
        conclusion="Reporting system verified. All sections render correctly with high-fidelity formatting.",
        overall_status="VERIFIED",
        recommendations=[
            "Standardize periodic automated audit generation.",
            "Integrate live execution markout analytics into weekly summaries.",
            "Extend rare-event simulations to include multi-asset correlation shocks.",
        ],
    )

    # 2. Market Regime Analysis
    orchestrator.add_section(
        RegimeSection(
            summary="Dominant bullish trending regime in Q1.",
            regimes=[
                RegimeSummary(
                    label="Bullish Trend",
                    frequency_pct=45.2,
                    avg_duration_bars=120,
                    profitability="High",
                ),
                RegimeSummary(
                    label="Ranging",
                    frequency_pct=30.8,
                    avg_duration_bars=45,
                    profitability="Neutral",
                ),
                RegimeSummary(
                    label="Mean Reversion",
                    frequency_pct=24.0,
                    avg_duration_bars=15,
                    profitability="Low",
                ),
            ],
            transition_insights="High stability in trending regimes with volatility-expansion triggers.",
        )
    )

    # 3. Stress Test Outcomes
    orchestrator.add_section(
        StressTestSection(
            resilience_score=82.5,
            baseline=StressedMetric(
                name="Baseline",
                total_return="18.2%",
                max_drawdown="4.5%",
                sharpe="2.4",
                recovery_factor="4.0",
                profit_factor="2.8",
                outcome="PASS",
            ),
            scenarios=[
                StressedMetric(
                    name="Execution Hell",
                    total_return="12.1%",
                    max_drawdown="6.8%",
                    sharpe="1.9",
                    recovery_factor="1.8",
                    profit_factor="1.9",
                    outcome="PASS",
                ),
                StressedMetric(
                    name="Liquidity Crisis",
                    total_return="5.4%",
                    max_drawdown="12.2%",
                    sharpe="0.8",
                    recovery_factor="0.4",
                    profit_factor="1.2",
                    outcome="PASS",
                ),
                StressedMetric(
                    name="Flash Crash",
                    total_return="-8.5%",
                    max_drawdown="22.4%",
                    sharpe="-0.4",
                    recovery_factor="0.0",
                    profit_factor="0.7",
                    outcome="FAIL",
                ),
            ],
            fragility_indicators=[
                "High sensitivity to wide spreads (>5 pips)",
                "Alpha decay during 5s+ latency spikes",
            ],
            failure_points=["Strategy breaks during >15 ATR intraday dislocations"],
        )
    )

    # 4. Hyperparameter Robustness
    orchestrator.add_section(
        HyperparameterSection(
            stability_score=78.0,
            parameters=[
                ParameterRobustness(
                    name="Fast Window", range="5-20", optimal="12", sensitivity="Low"
                ),
                ParameterRobustness(
                    name="Slow Window", range="21-60", optimal="48", sensitivity="Medium"
                ),
                ParameterRobustness(
                    name="Confidence Threshold", range="0.5-0.9", optimal="0.75", sensitivity="High"
                ),
            ],
            insights="Robust optimal found at (12, 48). High sensitivity to confidence threshold suggests narrow calibration window.",
        )
    )

    # 5. Trade Pattern Findings
    orchestrator.add_section(
        TradePatternSection(
            primary_insight="Strong performance in London/NY overlap; weakness in Sydney session.",
            concentrations=[
                PatternConcentration(
                    attribute="Session",
                    value="London",
                    win_rate=0.62,
                    profit_factor=2.4,
                    total_trades=145,
                ),
                PatternConcentration(
                    attribute="Algorithm",
                    value="Ensemble_V2",
                    win_rate=0.58,
                    profit_factor=2.1,
                    total_trades=210,
                ),
            ],
            behavioral_risks=[
                BehavioralRisk(
                    type="Overtrading",
                    description="Sydney session trade frequency 2x baseline with negative edge.",
                ),
                BehavioralRisk(
                    type="Toxic Motif",
                    description="PPO_Agent Buy in Extreme Volatility shows 15% win rate.",
                ),
            ],
            motifs=[
                SignalMotif(
                    algorithm="PPO",
                    direction=1,
                    volatility_bucket="Extreme",
                    confidence_bucket="Low",
                    session="Sydney",
                    frequency=12,
                    win_rate=0.15,
                )
            ],
            avg_win_duration=45.5,
            avg_loss_duration=18.2,
        )
    )

    # 6. Model Drift Observations
    orchestrator.add_section(
        ModelDriftSection(
            metrics=[
                DriftMetric(
                    name="Feature: RSI_14",
                    baseline="0.52",
                    current="0.58",
                    drift_pct=11.5,
                    status="STABLE",
                ),
                DriftMetric(
                    name="Feature: ATR_Ratio",
                    baseline="1.2",
                    current="2.1",
                    drift_pct=75.0,
                    status="CRITICAL",
                ),
            ],
            feature_shifts="ATR_Ratio has become the dominant predictor, indicating regime shift toward high-volatility breakout focus.",
        )
    )

    # 7. Capital Allocation Insights
    orchestrator.add_section(
        AllocationSection(
            total_heat_pct=55.0,
            allocations=[
                AllocationEntry(name="XAUUSD_PPO", amount="$55,000", heat_pct=55.0, multiplier=1.1),
                AllocationEntry(name="EURUSD_LSTM", amount="$0", heat_pct=0.0, multiplier=0.0),
            ],
            rejection_summary={"Total Heat Limit": 3, "Symbol Concentration": 1},
            diversification_score=0.45,
        )
    )

    # 8. Benchmark Comparisons
    orchestrator.add_section(
        BenchmarkSection(
            comparisons=[
                BenchmarkComparison(
                    name="Buy & Hold",
                    total_return="8.5%",
                    sharpe="0.9",
                    max_drawdown="15.2%",
                    p_value="0.001",
                ),
                BenchmarkComparison(
                    name="EMA Crossover",
                    total_return="12.4%",
                    sharpe="1.4",
                    max_drawdown="8.5%",
                    p_value="0.015",
                ),
            ],
            statistical_summary="Strategy significantly outperforms all technical and passive baselines at p < 0.05.",
        )
    )

    # 9. RL Agent Evaluation
    orchestrator.add_section(
        RLSection(
            comparison_summary="PPO_Agent outperforms Dreamer_V3 in trending regimes.",
            best_agent="PPO_Agent_V4",
            performance_gap=14.2,
            metrics=[
                RLMetric(
                    agent_name="PPO_Agent_V4",
                    sharpe=2.45,
                    sortino=3.1,
                    profit_factor=2.2,
                    max_dd=0.045,
                    win_rate=0.58,
                    recovery_factor=4.5,
                    var_95=0.012,
                    tail_ratio=1.85,
                    common_sense_ratio=4.07,
                    gain_to_pain_ratio=1.9,
                    sqn=6.2,
                    ulcer_index=0.015,
                    calmar=5.4,
                ),
                RLMetric(
                    agent_name="Dreamer_V3",
                    sharpe=1.92,
                    sortino=2.2,
                    profit_factor=1.7,
                    max_dd=0.082,
                    win_rate=0.52,
                    recovery_factor=2.1,
                    var_95=0.018,
                    tail_ratio=1.45,
                    common_sense_ratio=2.46,
                    gain_to_pain_ratio=1.4,
                    sqn=3.8,
                    ulcer_index=0.032,
                    calmar=2.3,
                ),
            ],
        )
    )

    # 10. Rare Event Simulations
    orchestrator.add_section(
        RareEventSection(
            scenarios=[
                RareEventSummary(
                    event_type="Flash Crash",
                    peak_impact_pct=-0.082,
                    realized_volatility=0.045,
                    recovery_attained=0.65,
                ),
                RareEventSummary(
                    event_type="Liquidity Vacuum",
                    peak_impact_pct=-0.021,
                    realized_volatility=0.015,
                    recovery_attained=1.0,
                ),
            ],
            insights="Resilient to vacuum events; 35% unrecovered loss during synthetic flash crashes.",
        )
    )

    # 11. Execution Quality
    orchestrator.add_section(
        ExecutionQualitySection(
            efficiency_score=91.5,
            metrics=[
                ExecutionMetric(name="Avg Slippage", value="0.45 pips", status="OK"),
                ExecutionMetric(name="Avg Latency", value="142ms", status="OK"),
                ExecutionMetric(name="Fill Quality", value="94.2%", status="OK"),
            ],
            opportunity_cost="$1,450.00",
            trade_count=156,
            rejected_count=42,
        )
    )

    # Build and Export
    report = orchestrator.build()
    reporter = ResearchReporter()

    md_path = "research_verification_report.md"
    html_path = "research_verification_report.html"

    reporter.save_markdown(report, md_path)
    reporter.save_html(report, html_path)

    print("\n✅ Verification complete!")
    print(f"   - Markdown: {os.path.abspath(md_path)}")
    print(f"   - HTML:     {os.path.abspath(html_path)}")

    # Terminal display check
    print("\n" + "=" * 50)
    reporter.format_for_terminal(report)


if __name__ == "__main__":
    main()

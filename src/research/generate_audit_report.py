"""
MT5 AI/ML Trading Bot - Enterprise Edition
src/research/generate_audit_report.py
Orchestration script to automatically generate comprehensive research audit reports.
"""

from __future__ import annotations

import os

from rich.console import Console

from src.research.reporting import (
    AllocationEntry,
    AllocationSection,
    BehavioralRisk,
    BenchmarkComparison,
    BenchmarkSection,
    DriftMetric,
    HyperparameterSection,
    ModelDriftSection,
    ParameterRobustness,
    PatternConcentration,
    RegimeSection,
    RegimeSummary,
    ResearchOrchestrator,
    ResearchReporter,
    StressedMetric,
    StressTestSection,
    TradePatternSection,
)


def generate_full_audit():
    """Generate a complete research audit report using mock data for demonstration."""
    console = Console()

    orchestrator = ResearchOrchestrator(
        title="XAUUSD Strategy Performance & Robustness Audit",
        executive_summary=(
            "This report provides a comprehensive evaluation of the AI trading system's performance, "
            "resilience, and consistency. Overall, the strategy demonstrates high stability in trending "
            "regimes but shows sensitivity to extreme news shocks. Capital allocation is well-diversified, "
            "and execution quality remains within institutional standards."
        ),
        conclusion="The strategy is suitable for deployment in production with a 'Verified' status, "
        "provided macro guardrails are active.",
        overall_status="VERIFIED",
        recommendations=[
            "Reduce risk multiplier during high-impact news windows.",
            "Recalibrate LSTM confidence thresholds every 30 days.",
            "Increase capital allocation to the London-NY session crossover.",
        ],
    )

    # 1. Regime Analysis
    regime_section = RegimeSection(
        summary="Market was primarily trending (65%) with high efficiency.",
        regimes=[
            RegimeSummary(
                label="Trending", frequency_pct=65.0, avg_duration_bars=45, profitability="High"
            ),
            RegimeSummary(
                label="Ranging", frequency_pct=25.0, avg_duration_bars=12, profitability="Neutral"
            ),
            RegimeSummary(
                label="News Shock",
                frequency_pct=10.0,
                avg_duration_bars=3,
                profitability="Low",
            ),
        ],
        transition_insights="Stability: 28.5 bars. Common paths: trending -> ranging (15.5%) | "
        "ranging -> news_shock (8.2%)",
    )
    orchestrator.add_section(regime_section)

    # 2. Stress Test Outcomes
    stress_section = StressTestSection(
        resilience_score=88.5,
        baseline=StressedMetric(
            name="Baseline",
            total_return="14.2%",
            max_drawdown="5.1%",
            sharpe="2.45",
            outcome="PASS",
        ),
        scenarios=[
            StressedMetric(
                name="Spread Widening (3x)",
                total_return="11.8%",
                max_drawdown="6.4%",
                sharpe="2.10",
                outcome="PASS",
            ),
            StressedMetric(
                name="Execution Hell",
                total_return="8.5%",
                max_drawdown="9.2%",
                sharpe="1.65",
                outcome="PASS",
            ),
            StressedMetric(
                name="Flash Crash",
                total_return="-2.1%",
                max_drawdown="18.5%",
                sharpe="-0.45",
                outcome="FAIL",
            ),
        ],
        fragility_indicators=[
            "High drawdown sensitivity to price noise > 1.5 sigma",
            "Latency impact > 500ms degrades alpha capture",
        ],
        failure_points=[
            "Sudden 2% price gap in < 1 minute",
            "Service failure during peak London volume",
        ],
    )
    orchestrator.add_section(stress_section)

    # 3. Hyperparameter Robustness
    hyper_section = HyperparameterSection(
        stability_score=92.0,
        parameters=[
            ParameterRobustness(
                name="fast_ema_window", range="5-25", optimal="12", sensitivity="Low"
            ),
            ParameterRobustness(
                name="confidence_threshold", range="0.5-0.9", optimal="0.65", sensitivity="Medium"
            ),
            ParameterRobustness(
                name="volatility_lookback", range="10-50", optimal="20", sensitivity="Low"
            ),
        ],
        insights="OOS Sharpe Mean: 2.15 | WFE: 0.88 | Worst OOS Sharpe: 1.45 | IS-OOS Gap: 0.25",
    )
    orchestrator.add_section(hyper_section)

    # 4. Trade Pattern Findings
    pattern_section = TradePatternSection(
        primary_insight="Critical behavioral risks identified: Overtrading during NY session.",
        concentrations=[
            PatternConcentration(
                attribute="algo_session",
                value="Ensemble @ London",
                win_rate=0.62,
                profit_factor=2.45,
                total_trades=145,
            ),
            PatternConcentration(
                attribute="algo_volatility",
                value="Ensemble @ Normal Vol",
                win_rate=0.58,
                profit_factor=2.10,
                total_trades=210,
            ),
        ],
        behavioral_risks=[
            BehavioralRisk(
                type="Overtrading",
                description="High trade frequency detected in NY session (4.2 trades/hour).",
            ),
            BehavioralRisk(
                type="Loss Clustering",
                description="Detected 2 clusters of 5+ losses during FOMC news shocks.",
            ),
        ],
        avg_win_duration=42.5,
        avg_loss_duration=18.2,
    )
    orchestrator.add_section(pattern_section)

    # 5. Model Drift Observations
    drift_section = ModelDriftSection(
        metrics=[
            DriftMetric(
                name="Target Distribution: close",
                baseline="2345.50",
                current="2342.10",
                drift_pct=2.4,
                status="STABLE",
            ),
            DriftMetric(
                name="Return Volatility",
                baseline="0.0012",
                current="0.0018",
                drift_pct=25.0,
                status="WARNING",
            ),
        ],
        feature_shifts="Significant shifts in: atr_ratio (+0.45), z_score (-0.32), vol_of_vol (+0.18)",
    )
    orchestrator.add_section(drift_section)

    # 6. Capital Allocation Insights
    alloc_section = AllocationSection(
        total_heat_pct=42.5,
        allocations=[
            AllocationEntry(
                name="ENSEMBLE_XAUUSD_M5", amount="$42,500.00", heat_pct=42.5, multiplier=1.15
            ),
            AllocationEntry(name="PPO_XAUUSD_M15", amount="$0.00", heat_pct=0.0, multiplier=0.85),
        ],
        rejection_summary={"TOTAL_HEAT_LIMIT": 0, "SYMBOL_CONCENTRATION_LIMIT": 2},
        diversification_score=0.85,
    )
    orchestrator.add_section(alloc_section)

    # 7. Benchmark Comparisons
    bench_section = BenchmarkSection(
        comparisons=[
            BenchmarkComparison(
                name="EMA_Crossover",
                total_return="8.5%",
                sharpe="1.20",
                max_drawdown="12.4%",
                p_value="0.0012",
                profit_factor="1.45",
            ),
            BenchmarkComparison(
                name="Momentum_ROC",
                total_return="6.2%",
                sharpe="0.95",
                max_drawdown="15.8%",
                p_value="0.0001",
                profit_factor="1.25",
            ),
        ],
        statistical_summary="Compared 2 strategies against Ensemble. 2 showed outperformance.",
    )
    orchestrator.add_section(bench_section)

    # Build and Export
    report = orchestrator.build()
    reporter = ResearchReporter()

    # Generate Terminal Output
    console.print("\n" + "=" * 80)
    console.print(" GENERATING RESEARCH AUDIT REPORT ".center(80, "="))
    console.print("=" * 80 + "\n")
    reporter.format_for_terminal(report)

    # Save Markdown and HTML
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    md_path = os.path.join(output_dir, "strategy_audit_report.md")
    html_path = os.path.join(output_dir, "strategy_audit_report.html")

    reporter.save_markdown(report, md_path)
    reporter.save_html(report, html_path)

    console.print("\n[bold green]SUCCESS:[/] Reports generated successfully:")
    console.print(f" - Markdown: [cyan]{md_path}[/]")
    console.print(f" - HTML:     [cyan]{html_path}[/]")


if __name__ == "__main__":
    generate_full_audit()

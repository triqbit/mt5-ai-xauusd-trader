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
    CalibrationBucket,
    CalibrationSection,
    CombinationMotif,
    DataQualitySection,
    DriftMetric,
    ExecutionMetric,
    ExecutionQualitySection,
    HyperparameterSection,
    MethodologySection,
    ModelDriftSection,
    ParameterRobustness,
    PatternConcentration,
    RareEventSection,
    RareEventSummary,
    RegimeSection,
    RegimeSummary,
    ResearchOrchestrator,
    ResearchReporter,
    RiskAuditSection,
    SectionStatus,
    SignalMotif,
    StrategicConfluenceSection,
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
        overall_status=SectionStatus.VERIFIED,
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
            recovery_factor="2.78",
            profit_factor="1.95",
            outcome="PASS",
        ),
        sharpe_decay=0.12,
        win_rate_decay=0.08,
        scenarios=[
            StressedMetric(
                name="Spread Widening (3x)",
                total_return="11.8%",
                max_drawdown="6.4%",
                sharpe="2.10",
                recovery_factor="1.84",
                profit_factor="1.62",
                outcome="PASS",
            ),
            StressedMetric(
                name="Execution Hell",
                total_return="8.5%",
                max_drawdown="9.2%",
                sharpe="1.65",
                recovery_factor="0.92",
                profit_factor="1.35",
                outcome="PASS",
            ),
            StressedMetric(
                name="Flash Crash",
                total_return="-2.1%",
                max_drawdown="18.5%",
                sharpe="-0.45",
                recovery_factor="-0.11",
                profit_factor="0.82",
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
        insights="The strategy shows exceptional resilience to execution delays and spread widening, "
        "maintaining a Profit Factor > 1.3 even in 'Execution Hell'. However, the Flash Crash "
        "scenario reveals a hard failure point where recovery factor collapses to negative levels.",
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
        walk_forward_efficiency=0.88,
        grade="A",
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
        motifs=[
            SignalMotif(
                algorithm="Ensemble",
                direction=1,
                volatility_bucket="Extreme",
                confidence_bucket="Low",
                session="New York",
                frequency=12,
                win_rate=0.25,
                expectancy=-1.45,
                efficiency_ratio=-0.32,
            )
        ],
        combinations=[
            CombinationMotif(
                patterns=["LSTM:1", "PPO:1"],
                frequency=8,
                avg_pnl_after=42.5,
                is_golden=True,
                expectancy=2.15,
                efficiency_ratio=0.65,
                session="London",
            ),
            CombinationMotif(
                patterns=["Transformer:-1", "PPO:1"],
                frequency=5,
                avg_pnl_after=-18.2,
                is_toxic=True,
                expectancy=-1.85,
                efficiency_ratio=-0.45,
                session="New York",
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
                psi_score=0.042,
                status="STABLE",
            ),
            DriftMetric(
                name="Return Volatility",
                baseline="0.0012",
                current="0.0018",
                drift_pct=25.0,
                psi_score=0.155,
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
                ulcer_index="1.42",
                lake_ratio="0.65",
                tail_ratio="0.85",
                common_sense_ratio="1.23",
                information_ratio="0.85",
                omega_ratio="1.42",
            ),
            BenchmarkComparison(
                name="Momentum_ROC",
                total_return="6.2%",
                sharpe="0.95",
                max_drawdown="15.8%",
                p_value="0.0001",
                profit_factor="1.25",
                ulcer_index="1.85",
                lake_ratio="0.72",
                tail_ratio="0.75",
                common_sense_ratio="0.94",
                information_ratio="0.42",
                omega_ratio="1.15",
            ),
        ],
        statistical_summary="Compared 2 strategies against Ensemble. 2 showed outperformance.",
    )
    orchestrator.add_section(bench_section)

    # 8. RL Evaluation
    from src.research.reporting import RLMetric, RLSection

    rl_section = RLSection(
        comparison_summary="Ensemble outperfoms baseline PPO by 15% in Sharpe.",
        best_agent="Ensemble_V2",
        performance_gap=15.2,
        metrics=[
            RLMetric(
                agent_name="Ensemble_V2",
                sharpe=2.85,
                sortino=3.20,
                volatility=0.12,
                profit_factor=2.15,
                expectancy=2.45,
                max_dd=0.08,
                win_rate=0.58,
                recovery_factor=4.50,
                lake_ratio=0.82,
                tail_ratio=1.45,
                sqn=3.10,
                var_95=0.015,
                common_sense_ratio=2.45,
                gain_to_pain_ratio=1.85,
            ),
            RLMetric(
                agent_name="Baseline_PPO",
                sharpe=1.95,
                sortino=2.10,
                volatility=0.18,
                profit_factor=1.65,
                expectancy=1.85,
                max_dd=0.14,
                win_rate=0.52,
                recovery_factor=2.80,
                lake_ratio=0.65,
                tail_ratio=1.10,
                sqn=1.85,
                var_95=0.025,
                common_sense_ratio=1.65,
                gain_to_pain_ratio=1.20,
            ),
        ],
    )
    orchestrator.add_section(rl_section)

    # 9. Rare Event Simulations
    rare_event_section = RareEventSection(
        scenarios=[
            RareEventSummary(
                event_type="Flash Crash (Synthetic)",
                peak_impact_pct=-0.085,
                realized_volatility=0.12,
                recovery_attained=0.95,
                description="Sudden 8.5% drop in XAUUSD with liquidity vacuum simulation.",
            ),
            RareEventSummary(
                event_type="Interest Rate Shock",
                peak_impact_pct=-0.042,
                realized_volatility=0.06,
                recovery_attained=1.0,
                description="Aggressive 50bps surprise hike impact.",
            ),
        ],
        insights="Strategy exhibits strong recovery capabilities, reclaiming 95% of 'Flash Crash' losses within 120 bars.",
    )
    orchestrator.add_section(rare_event_section)

    # 10. Calibration Analysis
    cal_section = CalibrationSection(
        brier_score=0.042,
        ece=0.035,
        mce=0.078,
        status="VERIFIED",
        optimal_threshold=0.68,
        buckets=[
            CalibrationBucket(range="0.5-0.6", accuracy=0.52, confidence=0.55, samples=120),
            CalibrationBucket(range="0.8-0.9", accuracy=0.84, confidence=0.85, samples=85),
            CalibrationBucket(range="0.9-1.0", accuracy=0.92, confidence=0.94, samples=42),
        ],
        reliability_insight="Model confidence is highly reliable above the 0.80 threshold. Recommended execution threshold: 0.68.",
    )
    orchestrator.add_section(cal_section)

    # 11. Execution Quality
    exec_section = ExecutionQualitySection(
        efficiency_score=94.2,
        trade_count=245,
        rejected_count=12,
        opportunity_cost="+$4,250.00",
        metrics=[
            ExecutionMetric(name="Avg Slippage (bps)", value="0.45", status="OK"),
            ExecutionMetric(name="Effective Spread Capture", value="82.5%", status="OK"),
            ExecutionMetric(name="Fill Rate", value="99.2%", status="OK"),
        ],
    )
    orchestrator.add_section(exec_section)

    # 12. Strategic Confluence
    confluence_section = StrategicConfluenceSection(
        confluence_score=0.86,
        regime_alignment=0.92,
        session_alignment=0.78,
        volatility_alignment=0.88,
        insights="EXCEPTIONAL: Signals show high alignment with London-NY overlap regimes. Caution in low-volatility drift states.",
    )
    orchestrator.add_section(confluence_section)

    # 13. Risk & Compliance Audit
    risk_audit_section = RiskAuditSection(
        status=SectionStatus.VERIFIED,
        portfolio_heat=0.425,
        hhi_score=0.125,
        drawdown_limit_compliance=True,
        leverage_compliance=True,
        audit_notes="Portfolio risk metrics are within institutional limits. HHI indicates healthy diversification.",
    )
    orchestrator.add_section(risk_audit_section)

    # 14. Data Quality
    data_quality_section = DataQualitySection(
        feed_health=99.8,
        missing_bars=5,
        stale_bars=2,
        gap_count=1,
        data_source="MetaAPI / XAUUSD_M5",
        status=SectionStatus.STABLE,
    )
    orchestrator.add_section(data_quality_section)

    # 15. Methodology
    methodology_section = MethodologySection(
        data_source="MetaAPI Tick Data / Dukascopy Historical",
        backtest_engine="High-Fidelity Discrete Event Simulator V4",
        lookback_period="2022-01-01 to 2024-03-31",
        assumptions=[
            "Fixed commission: $3.50 per lot",
            "Latency: Variable 50ms-250ms (Gamma distribution)",
            "Dynamic spread: Historical tick-based spreads",
        ],
        risk_limits=[
            "Max drawdown: 15%",
            "Max daily loss: 3%",
            "Max leverage: 1:20",
        ],
    )
    orchestrator.add_section(methodology_section)

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

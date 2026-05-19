"""
Tests for the research reporting system.
"""

import os

import pytest

from src.research.reporting import (
    AllocationEntry,
    AllocationSection,
    CombinationMotif,
    DataQualitySection,
    RareEventSection,
    RareEventSummary,
    RegimeSection,
    RegimeSummary,
    ResearchOrchestrator,
    ResearchReport,
    ResearchReporter,
    RiskAuditSection,
    SectionStatus,
    SignalMotif,
    StressedMetric,
    StressTestSection,
    TradePatternSection,
)


@pytest.fixture
def sample_report():
    return ResearchReport(
        title="Q1 2024 Strategy Robustness Audit",
        executive_summary="The strategy shows high resilience but sensitive to news shocks.",
        regime_analysis=RegimeSection(
            summary="Market was primarily trending with low volatility.",
            regimes=[
                RegimeSummary(
                    label="Trending", frequency_pct=65.0, avg_duration_bars=45, profitability="High"
                ),
                RegimeSummary(
                    label="Ranging", frequency_pct=25.0, avg_duration_bars=12, profitability="Low"
                ),
            ],
            transition_insights="Slow transitions between trending and ranging regimes.",
        ),
        stress_tests=StressTestSection(
            resilience_score=85.5,
            baseline=StressedMetric(
                name="Baseline",
                total_return="12.5%",
                max_drawdown="4.2%",
                sharpe="2.1",
                outcome="PASS",
            ),
            scenarios=[
                StressedMetric(
                    name="Spread Widening",
                    total_return="10.1%",
                    max_drawdown="5.8%",
                    sharpe="1.8",
                    outcome="PASS",
                ),
                StressedMetric(
                    name="News Shock",
                    total_return="-2.5%",
                    max_drawdown="15.2%",
                    sharpe="-0.5",
                    outcome="FAIL",
                ),
            ],
            fragility_indicators=["High drawdown during volatility spikes"],
            failure_points=["Sudden 50bp price jumps"],
        ),
        allocation_insights=AllocationSection(
            total_heat_pct=45.0,
            allocations=[
                AllocationEntry(name="XAUUSD_PPO", amount="$45,000", heat_pct=45.0, multiplier=1.2)
            ],
            rejection_summary={"Symbol concentration": 5},
        ),
        conclusion="Recommend deploying with reduced size during high-impact news.",
    )


def test_markdown_generation(sample_report):
    sample_report.stress_tests.insights = "Tested with high fidelity."
    sample_report.stress_tests.baseline.recovery_factor = "2.5"
    sample_report.stress_tests.baseline.profit_factor = "1.8"

    reporter = ResearchReporter()
    markdown = reporter.generate_markdown(sample_report)

    assert "# Q1 2024 Strategy Robustness Audit" in markdown
    assert "Market Regime Analysis" in markdown
    assert "Trending" in markdown
    assert "65.0%" in markdown
    assert "Stress Test Outcomes" in markdown
    assert "Resilience Score" in markdown
    assert "85.5/100" in markdown
    assert "Spread Widening" in markdown
    assert "PASS" in markdown
    assert "Capital Allocation Insights" in markdown
    assert "XAUUSD_PPO" in markdown
    assert "$45,000" in markdown
    assert "Recommend deploying" in markdown

    # New fields
    assert "Analytical Insights:" in markdown
    assert "Tested with high fidelity." in markdown
    assert "2.5" in markdown
    assert "1.8" in markdown
    assert "Win Rate Decay:" in markdown


def test_terminal_formatting(sample_report, capsys):
    reporter = ResearchReporter()
    reporter.format_for_terminal(sample_report)
    captured = capsys.readouterr()

    assert "Q1 2024 Strategy Robustness Audit" in captured.out
    assert "Market Regime Analysis" in captured.out
    assert "Stress Test Outcomes" in captured.out
    assert "Resilience Score: 85.5/100" in captured.out
    assert "Capital Allocation" in captured.out


def test_save_markdown(sample_report, tmp_path):
    reporter = ResearchReporter()
    file_path = tmp_path / "test_report.md"
    reporter.save_markdown(sample_report, str(file_path))

    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        content = f.read()
        assert "Q1 2024 Strategy Robustness Audit" in content


def test_research_orchestrator():
    orchestrator = ResearchOrchestrator(
        title="Orchestrated Report", executive_summary="Summary", conclusion="Conclusion"
    )

    regime = RegimeSection(
        summary="Test Summary",
        regimes=[
            RegimeSummary(
                label="Trending", frequency_pct=50, avg_duration_bars=10, profitability="Neutral"
            )
        ],
        transition_insights="None",
    )

    orchestrator.add_section(regime)
    report = orchestrator.build()

    assert report.title == "Orchestrated Report"
    assert report.regime_analysis is not None
    assert report.regime_analysis.summary == "Test Summary"


def test_rare_event_reporting():
    rare_event_section = RareEventSection(
        scenarios=[
            RareEventSummary(
                event_type="flash_crash",
                peak_impact_pct=-0.05,
                realized_volatility=0.1,
                recovery_attained=0.8,
            )
        ],
        insights="Resilient to small crashes.",
    )

    report = ResearchReport(
        title="Rare Event Audit",
        executive_summary="Testing rare events.",
        rare_events=rare_event_section,
        conclusion="Final.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    assert "Rare Event Simulations" in md
    assert "flash_crash" in md
    assert "-5.0%" in md
    assert "80.0%" in md

    assert "Rare Event Simulations" in html
    assert "flash_crash" in html
    assert 'href="#rare-events"' in html
    assert 'role="progressbar"' not in html  # No stress tests here


def test_calibration_reporting():
    """Verify that CalibrationResult integrates with the reporting system."""
    from src.models.calibration import CalibrationResult, ConfidenceBucket

    buckets = [
        ConfidenceBucket(
            range_start=0.5,
            range_end=0.6,
            avg_confidence=0.55,
            accuracy=0.52,
            sample_count=10,
            deviation=0.03,
        ),
        ConfidenceBucket(
            range_start=0.9,
            range_end=1.0,
            avg_confidence=0.95,
            accuracy=0.92,
            sample_count=5,
            deviation=0.03,
        ),
    ]
    cal_res = CalibrationResult(
        brier_score=0.05,
        reliability=0.02,
        resolution=0.1,
        uncertainty=0.15,
        ece=0.04,
        mce=0.08,
        buckets=buckets,
        optimal_threshold=0.65,
        status="VERIFIED",
    )

    report = ResearchReport(
        title="Calibration Audit",
        executive_summary="Testing calibration.",
        calibration_analysis=cal_res.to_report_section(),
        conclusion="Calibrated.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    assert "Confidence Calibration & Reliability" in md
    assert "0.04" in md  # ECE
    assert "0.5-0.6" in md
    assert "92.0%" in md

    assert "Confidence Calibration & Reliability" in html
    assert "VERIFIED" in html
    assert "0.04" in html
    assert "0.65" in html


def test_html_dynamic_elements(sample_report):
    """Verify TOC, dynamic numbering and progress bars in HTML."""
    reporter = ResearchReporter()
    html = reporter.generate_html(sample_report)

    # TOC and Navigation
    assert "Table of Contents" in html
    assert 'href="#executive-summary"' in html
    assert 'href="#regime-analysis"' in html
    assert 'href="#stress-tests"' in html

    # Dynamic Numbering in TOC (Executive Summary is 1, Regime is 2, Stress is 3, Allocation is 4, Conclusion is 5)
    assert "1. Executive Summary" in html
    assert "2. Market Regime Analysis" in html
    assert "3. Stress Test Outcomes" in html
    assert "4. Capital Allocation Insights" in html
    assert "5. Conclusion & Recommendations" in html

    # Progress Bars (ARIA)
    assert 'role="progressbar"' in html
    assert 'aria-valuenow="85.5"' in html

    # Accessibility
    assert 'scope="col"' in html


def test_html_ux_enhancements(sample_report):
    """Verify smooth scroll, back-to-top and color coding in HTML."""
    reporter = ResearchReporter()
    html = reporter.generate_html(sample_report)

    # Smooth scroll
    assert "scroll-behavior: smooth;" in html

    # Back to top button
    assert 'class="back-to-top"' in html
    assert 'aria-label="Scroll back to top"' in html

    # Color coding classes
    assert ".fill-low" in html
    assert ".fill-medium" in html
    assert ".fill-high" in html

    # Resilience score is 85.5 -> should have fill-high
    assert "fill-high" in html
    assert 'aria-label="Strategy resilience score: 85.5 out of 100"' in html


def test_html_accessibility_hardening(sample_report):
    """Verify accessibility and print hardening in HTML."""
    reporter = ResearchReporter()
    html = reporter.generate_html(sample_report)

    # Skip to main content link
    assert 'class="skip-link"' in html
    assert 'href="#main-content"' in html
    assert "Skip to main content" in html

    # Semantic main tag
    assert '<main id="main-content">' in html
    assert "</main>" in html

    # ARIA labels
    assert 'role="banner"' in html
    assert 'aria-label="Main Navigation"' in html
    assert 'aria-label="Print research report"' in html
    assert 'aria-hidden="true"' in html  # For the back-to-top icon

    # Print styles
    assert "@media print" in html
    assert ".print-btn" in html
    assert "window['print']()" in html


def test_critical_warnings_panel():
    """Verify that the critical warnings panel appears when there are issues."""
    from src.research.reporting import DriftMetric, ModelDriftSection

    report = ResearchReport(
        title="Warning Test",
        executive_summary="Summary",
        model_drift=ModelDriftSection(
            metrics=[
                DriftMetric(
                    name="Test", baseline="1", current="2", drift_pct=100.0, status="CRITICAL"
                )
            ],
            feature_shifts="None",
        ),
        conclusion="Conclusion",
    )

    reporter = ResearchReporter()
    html = reporter.generate_html(report)

    assert "Critical Research Warnings" in html
    assert "CRITICAL" in html


def test_trade_pattern_motifs():
    trade_section = TradePatternSection(
        primary_insight="Insight",
        concentrations=[],
        behavioral_risks=[],
        motifs=[
            SignalMotif(
                algorithm="PPO",
                direction=1,
                volatility_bucket="High",
                confidence_bucket="Low",
                frequency=5,
                win_rate=0.2,
                expectancy=-1.5,
                efficiency_ratio=-0.4,
                session="Asian",
            )
        ],
        combinations=[
            CombinationMotif(
                patterns=["Algo1:1", "Algo2:-1"],
                frequency=3,
                avg_pnl_after=-10.0,
                is_toxic=True,
                expectancy=-2.0,
                efficiency_ratio=-0.5,
            )
        ],
    )

    report = ResearchReport(
        title="Motif Audit",
        executive_summary="Testing motifs.",
        trade_patterns=trade_section,
        conclusion="Final.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    # Markdown checks
    assert "### Signal Motifs (Performance Clusters)" in md
    assert "PPO" in md
    assert "20.0%" in md
    assert "-1.5" in md
    assert "-0.4" in md
    assert "### Signal Combinations (Toxic vs Golden)" in md
    assert "Algo1:1, Algo2:-1" in md
    assert "TOXIC" in md
    assert "-2.0" in md

    # HTML checks
    assert "Signal Motifs (Performance Clusters)" in html
    assert "PPO" in html
    assert "20.0%" in html
    assert "-1.5" in html
    assert "Signal Combinations (Toxic vs Golden)" in html
    assert "Algo1:1, Algo2:-1" in html
    assert "TOXIC" in html


def test_rl_evaluation_reporting():
    from src.research.reporting import RLMetric, RLSection

    rl_section = RLSection(
        comparison_summary="Better than baseline.",
        best_agent="Agent_V2",
        performance_gap=15.5,
        metrics=[
            RLMetric(
                agent_name="Agent_V2",
                sharpe=2.1,
                sortino=2.5,
                profit_factor=1.8,
                max_dd=0.12,
                win_rate=0.6,
                recovery_factor=4.2,
            )
        ],
    )

    report = ResearchReport(
        title="RL Audit",
        executive_summary="Testing RL.",
        rl_evaluation=rl_section,
        conclusion="Final.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    assert "RL Agent Evaluation" in md
    assert "Agent_V2" in md
    assert "2.5" in md
    assert "4.2" in md

    assert "RL Agent Evaluation" in html
    assert "Agent_V2" in html
    assert 'href="#rl-evaluation"' in html


def test_rl_metric_new_fields():
    from src.research.reporting import RLMetric

    metric = RLMetric(
        agent_name="TestAgent",
        sharpe=1.5,
        volatility=0.15,
        profit_factor=1.2,
        expectancy=0.45,
        max_dd=0.1,
        win_rate=0.5,
        tail_ratio=1.8,
        common_sense_ratio=2.1,
        gain_to_pain_ratio=1.4,
    )
    assert metric.volatility == 0.15
    assert metric.expectancy == 0.45
    assert metric.tail_ratio == 1.8
    assert metric.common_sense_ratio == 2.1
    assert metric.gain_to_pain_ratio == 1.4


def test_pattern_concentration_total_trades():
    from src.research.reporting import PatternConcentration

    pc = PatternConcentration(
        attribute="Algo", value="PPO", win_rate=0.6, profit_factor=2.0, total_trades=100
    )
    assert pc.total_trades == 100


def test_terminal_dynamic_numbering(mocker):
    """Verify that terminal output uses dynamic numbering for sections."""
    from src.research.reporting import (
        RegimeSection,
        ResearchReport,
        ResearchReporter,
        RLSection,
    )

    # Mock console.print to capture output
    mock_console = mocker.patch("src.research.reporting.Console")
    reporter = ResearchReporter()
    reporter.console = mock_console.return_value

    report = ResearchReport(
        title="Test Report",
        executive_summary="Summary",
        conclusion="Conclusion",
    )

    # Add only Regime Analysis (Section 1) and RL Evaluation (should be Section 2, not 8)
    report.regime_analysis = RegimeSection(
        summary="Regime summary", regimes=[], transition_insights="None"
    )
    report.rl_evaluation = RLSection(
        comparison_summary="RL summary", best_agent="PPO", performance_gap=0.0, metrics=[]
    )

    reporter.format_for_terminal(report)

    # Check that console.print was called with sequential numbers
    calls = [c[0][0] for c in reporter.console.print.call_args_list if isinstance(c[0][0], str)]

    # We expect "1. Market Regime Analysis" and "2. RL Agent Evaluation"
    # Note: reporting.py uses f"\n[bold cyan]{section_idx}. Market Regime Analysis[/]"

    found_regime = any("1. Market Regime Analysis" in s for s in calls)
    found_rl = any("2. RL Agent Evaluation" in s for s in calls)

    assert found_regime, f"Regime analysis header not found in: {calls}"
    assert found_rl, (
        f"RL Evaluation should be section 2, but header not found correctly in: {calls}"
    )


def test_risk_audit_reporting():
    """Verify RiskAuditSection reporting."""
    risk_section = RiskAuditSection(
        status=SectionStatus.VERIFIED,
        portfolio_heat=0.45,
        hhi_score=0.12,
        drawdown_limit_compliance=True,
        leverage_compliance=True,
        audit_notes="Portfolio risk is well-contained.",
    )

    report = ResearchReport(
        title="Risk Audit",
        executive_summary="Testing risk.",
        risk_audit=risk_section,
        conclusion="Safe.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    assert "Risk & Compliance Audit" in md
    assert "45.0%" in md
    assert "Portfolio risk is well-contained." in md

    assert "Risk & Compliance Audit" in html
    assert "VERIFIED" in html.upper()
    assert "0.12" in html


def test_data_quality_reporting():
    """Verify DataQualitySection reporting."""
    data_section = DataQualitySection(
        feed_health=98.5,
        missing_bars=10,
        stale_bars=5,
        gap_count=2,
        data_source="MetaAPI",
        status=SectionStatus.STABLE,
    )

    report = ResearchReport(
        title="Data Audit",
        executive_summary="Testing data.",
        data_quality=data_section,
        conclusion="Data is clean.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    html = reporter.generate_html(report)

    assert "Data Integrity & Quality" in md
    assert "98.5%" in md
    assert "MetaAPI" in md

    assert "Data Integrity & Quality" in html
    assert "STABLE" in html.upper()
    assert "98.5%" in html
    assert "Gaps Detected" in html


def test_enhanced_stress_test_reporting():
    """Verify enhanced StressTestSection with decay fields."""
    stress_section = StressTestSection(
        resilience_score=92.0,
        baseline=StressedMetric(
            name="Baseline", total_return="10%", max_drawdown="5%", sharpe="2.0", outcome="PASS"
        ),
        scenarios=[],
        sharpe_decay=0.15,
        win_rate_decay=0.05,
    )

    report = ResearchReport(
        title="Stress Audit",
        executive_summary="Summary",
        stress_tests=stress_section,
        conclusion="Robust.",
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)
    assert "**Sharpe Decay:** 15.0%" in md
    assert "**Win Rate Decay:** 5.0%" in md


def test_generate_audit_report_smoke_test():
    """Verify that the audit report generation script runs without error."""
    import os

    from src.research.generate_audit_report import generate_full_audit

    # Run the generation
    generate_full_audit()

    # Verify outputs exist
    assert os.path.exists("reports/strategy_audit_report.md")
    assert os.path.exists("reports/strategy_audit_report.html")

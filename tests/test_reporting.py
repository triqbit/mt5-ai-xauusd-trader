"""
Tests for the research reporting system.
"""

import os

import pytest

from src.research.reporting import (
    AllocationEntry,
    AllocationSection,
    RegimeSection,
    RegimeSummary,
    ResearchReport,
    ResearchReporter,
    StressedMetric,
    StressTestSection,
    ResearchOrchestrator,
    RareEventSection,
    RareEventSummary,
    TradePatternSection,
    SignalMotif,
)


@pytest.fixture
def sample_report():
    return ResearchReport(
        title="Q1 2024 Strategy Robustness Audit",
        executive_summary="The strategy shows high resilience but sensitive to news shocks.",
        regime_analysis=RegimeSection(
            summary="Market was primarily trending with low volatility.",
            regimes=[
                RegimeSummary(label="Trending", frequency_pct=65.0, avg_duration_bars=45, profitability="High"),
                RegimeSummary(label="Ranging", frequency_pct=25.0, avg_duration_bars=12, profitability="Low"),
            ],
            transition_insights="Slow transitions between trending and ranging regimes."
        ),
        stress_tests=StressTestSection(
            resilience_score=85.5,
            baseline=StressedMetric(name="Baseline", total_return="12.5%", max_drawdown="4.2%", sharpe="2.1", outcome="PASS"),
            scenarios=[
                StressedMetric(name="Spread Widening", total_return="10.1%", max_drawdown="5.8%", sharpe="1.8", outcome="PASS"),
                StressedMetric(name="News Shock", total_return="-2.5%", max_drawdown="15.2%", sharpe="-0.5", outcome="FAIL"),
            ],
            fragility_indicators=["High drawdown during volatility spikes"],
            failure_points=["Sudden 50bp price jumps"]
        ),
        allocation_insights=AllocationSection(
            total_heat_pct=45.0,
            allocations=[
                AllocationEntry(name="XAUUSD_PPO", amount="$45,000", heat_pct=45.0, multiplier=1.2)
            ],
            rejection_summary={"Symbol concentration": 5}
        ),
        conclusion="Recommend deploying with reduced size during high-impact news."
    )

def test_markdown_generation(sample_report):
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
        title="Orchestrated Report",
        executive_summary="Summary",
        conclusion="Conclusion"
    )

    regime = RegimeSection(
        summary="Test Summary",
        regimes=[RegimeSummary(label="Trending", frequency_pct=50, avg_duration_bars=10, profitability="Neutral")],
        transition_insights="None"
    )

    orchestrator.add_section(regime)
    report = orchestrator.build()

    assert report.title == "Orchestrated Report"
    assert report.regime_analysis is not None
    assert report.regime_analysis.summary == "Test Summary"

def test_rare_event_reporting():
    rare_event_section = RareEventSection(
        scenarios=[
            RareEventSummary(event_type="flash_crash", peak_impact_pct=-0.05, realized_volatility=0.1, recovery_attained=0.8)
        ],
        insights="Resilient to small crashes."
    )

    report = ResearchReport(
        title="Rare Event Audit",
        executive_summary="Testing rare events.",
        rare_events=rare_event_section,
        conclusion="Final."
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
    assert 'role="progressbar"' not in html # No stress tests here

def test_html_dynamic_elements(sample_report):
    """Verify TOC, dynamic numbering and progress bars in HTML."""
    reporter = ResearchReporter()
    html = reporter.generate_html(sample_report)

    # TOC and Navigation
    assert 'Table of Contents' in html
    assert 'href="#executive-summary"' in html
    assert 'href="#regime-analysis"' in html
    assert 'href="#stress-tests"' in html

    # Dynamic Numbering in TOC (Executive Summary is 1, Regime is 2, Stress is 3, Allocation is 4, Conclusion is 5)
    assert '1. Executive Summary' in html
    assert '2. Market Regime Analysis' in html
    assert '3. Stress Test Outcomes' in html
    assert '4. Capital Allocation Insights' in html
    assert '5. Conclusion & Recommendations' in html

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
    assert 'scroll-behavior: smooth;' in html

    # Back to top button
    assert 'class="back-to-top"' in html
    assert 'aria-label="Scroll back to top"' in html

    # Color coding classes
    assert '.fill-low' in html
    assert '.fill-medium' in html
    assert '.fill-high' in html

    # Resilience score is 85.5 -> should have fill-high
    assert 'fill-high' in html
    assert 'aria-label="Strategy resilience score: 85.5 out of 100"' in html

def test_html_accessibility_hardening(sample_report):
    """Verify accessibility and print hardening in HTML."""
    reporter = ResearchReporter()
    html = reporter.generate_html(sample_report)

    # Skip to main content link
    assert 'class="skip-link"' in html
    assert 'href="#main-content"' in html
    assert 'Skip to main content' in html

    # Semantic main tag
    assert '<main id="main-content">' in html
    assert '</main>' in html

    # ARIA labels
    assert 'role="banner"' in html
    assert 'aria-label="Main Navigation"' in html
    assert 'aria-label="Print research report"' in html
    assert 'aria-hidden="true"' in html  # For the back-to-top icon

    # Print styles
    assert '@media print' in html
    assert '.print-btn' in html
    assert 'window[\'print\']()' in html

def test_trade_pattern_motifs():
    trade_section = TradePatternSection(
        primary_insight="Insight",
        concentrations=[],
        behavioral_risks=[],
        motifs=[
            SignalMotif(algorithm="PPO", direction=1, volatility_bucket="High", confidence_bucket="Low", frequency=5, win_rate=0.2)
        ]
    )

    report = ResearchReport(
        title="Motif Audit",
        executive_summary="Testing motifs.",
        trade_patterns=trade_section,
        conclusion="Final."
    )

    reporter = ResearchReporter()
    md = reporter.generate_markdown(report)

    assert "### Signal Motifs (Losing Combinations)" in md
    assert "PPO" in md
    assert "20.0%" in md

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
                recovery_factor=4.2
            )
        ]
    )

    report = ResearchReport(
        title="RL Audit",
        executive_summary="Testing RL.",
        rl_evaluation=rl_section,
        conclusion="Final."
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
        profit_factor=1.2,
        max_dd=0.1,
        win_rate=0.5,
        tail_ratio=1.8,
        common_sense_ratio=2.1,
        gain_to_pain_ratio=1.4
    )
    assert metric.tail_ratio == 1.8
    assert metric.common_sense_ratio == 2.1
    assert metric.gain_to_pain_ratio == 1.4

def test_pattern_concentration_total_trades():
    from src.research.reporting import PatternConcentration
    pc = PatternConcentration(
        attribute="Algo",
        value="PPO",
        win_rate=0.6,
        profit_factor=2.0,
        total_trades=100
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
    assert found_rl, f"RL Evaluation should be section 2, but header not found correctly in: {calls}"

"""
Tests for the enhanced research reporting system v3.
"""

from src.research.reporting import (
    DriftMetric,
    MethodologySection,
    ModelDriftSection,
    ResearchOrchestrator,
    ResearchReport,
    ResearchReporter,
    StrategicConfluenceSection,
)


def test_enhanced_sections_integration():
    """Verify that new sections integrate correctly with the orchestrator and reporter."""
    orchestrator = ResearchOrchestrator(
        title="Enhanced Audit",
        executive_summary="Testing new sections.",
        conclusion="Conclusion."
    )

    # 1. Test DriftMetric with psi_score
    drift_section = ModelDriftSection(
        metrics=[
            DriftMetric(
                name="Test Metric",
                baseline="100",
                current="105",
                drift_pct=5.0,
                psi_score=0.042,
                status="STABLE"
            )
        ],
        feature_shifts="None"
    )
    orchestrator.add_section(drift_section)

    # 2. Test StrategicConfluenceSection
    confluence = StrategicConfluenceSection(
        confluence_score=0.85,
        regime_alignment=0.9,
        session_alignment=0.8,
        volatility_alignment=0.7,
        insights="High alignment detected."
    )
    orchestrator.add_section(confluence)

    # 3. Test MethodologySection
    methodology = MethodologySection(
        data_source="Test Source",
        backtest_engine="Test Engine",
        lookback_period="2023-2024",
        assumptions=["Assumption 1"],
        risk_limits=["Limit 1"]
    )
    orchestrator.add_section(methodology)

    report = orchestrator.build()
    reporter = ResearchReporter()

    # Verify Markdown rendering
    md = reporter.generate_markdown(report)
    assert "Model Drift Observations" in md
    assert "PSI" in md
    assert "0.042" in md
    assert "Strategic Confluence Analysis" in md
    assert "85.0%" in md
    assert "Methodology & Audit Trail" in md
    assert "Test Source" in md
    assert "Assumption 1" in md

    # Verify HTML rendering
    html = reporter.generate_html(report)
    assert "Strategic Confluence Analysis" in html
    assert "confluence_score * 100" not in html # ensure it's rendered not raw template
    assert "85.0%" in html
    assert "PSI" in html
    assert "0.042" in html
    assert "Methodology & Audit Trail" in html

def test_terminal_output_new_sections(capsys):
    """Verify terminal formatting for new sections."""
    report = ResearchReport(
        title="Terminal Test",
        executive_summary="Testing terminal.",
        strategic_confluence=StrategicConfluenceSection(
            confluence_score=0.85,
            regime_alignment=0.9,
            session_alignment=0.8,
            volatility_alignment=0.7,
            insights="High alignment detected."
        ),
        methodology=MethodologySection(
            data_source="Source",
            backtest_engine="Engine",
            lookback_period="Period",
            assumptions=[],
            risk_limits=[]
        ),
        conclusion="Done."
    )

    reporter = ResearchReporter()
    reporter.format_for_terminal(report)
    captured = capsys.readouterr()

    assert "Strategic Confluence Analysis" in captured.out
    assert "85.0%" in captured.out
    assert "Methodology & Audit Trail" in captured.out
    assert "Data Source: Source" in captured.out

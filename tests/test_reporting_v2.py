"""
Extended tests for the research reporting system.
Focuses on overall status and actionable recommendations.
"""

from src.research.reporting import ResearchOrchestrator, ResearchReporter


def test_reporting_v2_status_and_recommendations():
    orchestrator = ResearchOrchestrator(
        title="V2 Test Report",
        executive_summary="Summary",
        conclusion="Conclusion",
        overall_status="PROVISIONAL"
    )

    orchestrator.add_recommendation("Recommendation 1")
    orchestrator.add_recommendation("Recommendation 2")
    orchestrator.set_status("VERIFIED")

    report = orchestrator.build()

    assert report.overall_status == "VERIFIED"
    assert len(report.recommendations) == 2
    assert "Recommendation 1" in report.recommendations
    assert "Recommendation 2" in report.recommendations

def test_v2_template_rendering():
    orchestrator = ResearchOrchestrator(
        title="V2 Rendering Test",
        executive_summary="Summary",
        conclusion="Strategic Conclusion",
        overall_status="VERIFIED",
        recommendations=["Action 1", "Action 2"]
    )

    report = orchestrator.build()
    reporter = ResearchReporter()

    # Verify HTML Rendering
    html = reporter.generate_html(report)
    assert "status-verified" in html
    assert "VERIFIED" in html
    assert "Actionable Recommendations" in html
    assert "Action 1" in html
    assert "Action 2" in html
    assert "Strategic Conclusion" in html

    # Verify Markdown Rendering
    md = reporter.generate_markdown(report)
    assert "- **Status:** VERIFIED" in md
    assert "Actionable Recommendations:" in md
    assert "- Action 1" in md
    assert "- Action 2" in md
    assert "Strategic Conclusion" in md

def test_terminal_formatting_v2(capsys):
    orchestrator = ResearchOrchestrator(
        title="Terminal V2 Test",
        executive_summary="Summary",
        conclusion="Conclusion",
        overall_status="VERIFIED",
        recommendations=["Rec A"]
    )
    report = orchestrator.build()
    reporter = ResearchReporter()

    reporter.format_for_terminal(report)
    captured = capsys.readouterr()

    # Rich strips tags when rendering to non-interactive console by default
    # But it still prints the content
    assert "Status: VERIFIED" in captured.out
    assert "Recommendations" in captured.out
    assert "- Rec A" in captured.out

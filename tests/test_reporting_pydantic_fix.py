from datetime import datetime

from src.research.reporting import ResearchReport


def test_research_report_instantiation():
    """Verify ResearchReport can be instantiated with required fields."""
    report = ResearchReport(
        title="CI Fix Test",
        executive_summary="Summary",
        conclusion="Conclusion"
    )
    assert report.title == "CI Fix Test"
    assert report.executive_summary == "Summary"
    assert report.conclusion == "Conclusion"
    assert isinstance(report.timestamp, datetime)

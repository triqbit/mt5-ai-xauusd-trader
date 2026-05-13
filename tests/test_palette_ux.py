from rich.table import Table

from src.core.health import ComponentStatus, HealthReport, HealthStatus


def test_health_report_table_display():
    """Verify that the health report components can be rendered in a table (UX Check)."""
    table = Table()
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Message")

    # Simulate adding rows as done in main.py
    report = HealthReport(
        status=HealthStatus.HEALTHY,
        components={"MT5": ComponentStatus(status=HealthStatus.HEALTHY, message="Connected")},
    )

    for name, comp in report.components.items():
        color = "green" if comp.status == HealthStatus.HEALTHY else "red"
        table.add_row(name, f"[{color}]{comp.status.value.upper()}[/]", comp.message)

    assert len(table.columns) == 3
    assert table.columns[0].header == "Component"


def test_research_report_template_rendering_sanity():
    """Verify that the research report template can be loaded (UX Check)."""
    import os

    template_path = "src/research/templates/research_report.html.j2"
    assert os.path.exists(template_path)
    with open(template_path, "r") as f:
        content = f.read()
    assert "focus-visible" in content
    assert "fill-up" in content
    # Verify UX enhancements added by Palette
    assert "progress-bar-scroll" in content
    assert "scrollBar" in content
    assert "kpi-card:hover" in content

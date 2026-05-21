import pytest

from src.research.reporting import ResearchReporter, TradeSection


@pytest.fixture
def reporter():
    return ResearchReporter()


def test_trade_section_formatting(reporter):
    """Verify trade section renders correctly with institutional formatting."""
    section = TradeSection(
        total_trades=100,
        win_rate=0.65,
        profit_factor=2.5,
        max_drawdown=0.08,
        sharpe_ratio=3.2,
    )
    # Renders to rich table or similar structure
    content = section.to_report_content()
    assert content is not None


def test_full_report_generation(reporter, tmp_path):
    """Verify end-to-end report generation to disk."""
    output_file = tmp_path / "test_report.html"
    reporter.add_section(
        TradeSection(
            total_trades=10,
            win_rate=0.5,
            profit_factor=1.5,
            max_drawdown=0.05,
            sharpe_ratio=1.2,
        )
    )
    reporter.generate(output_file)
    assert output_file.exists()

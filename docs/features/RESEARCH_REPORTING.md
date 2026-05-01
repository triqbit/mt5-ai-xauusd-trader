# Institutional Research Reporting

The institutional research reporting system automatically generates high-quality summaries of trading strategy performance, robustness, and behavior. These reports are designed for Portfolio Managers, Quant Leads, and Auditors.

## Features

- **Multi-Section Summaries**:
    - **Regime Analysis**: Insights into market states and strategy performance per regime.
    - **Stress Test Outcomes**: Resilience scores and performance under adverse conditions.
    - **Hyperparameter Robustness**: Stability analysis of model parameters.
    - **Trade Pattern Findings**: Behavioral insights from journal mining (e.g., overtrading, profitable concentrations).
    - **Model Drift Observations**: Tracking of feature importance shifts and metric decay.
    - **Capital Allocation Insights**: Portfolio heat tracking and allocation multipliers.
    - **Benchmark Comparisons**: Statistical performance evaluation against baseline strategies (EMA Crossover, Momentum, Volatility Breakout, Mean Reversion).

- **Flexible Output Formats**:
    - **Markdown**: Beautiful, export-friendly reports generated via Jinja2 templates.
    - **Terminal**: Scannable, interactive dashboards using the `rich` library.

## Usage

### Generating a Report

```python
from src.research.reporting import ResearchReporter, ResearchReport

# Initialize reporter
reporter = ResearchReporter()

# Create a report object (usually aggregated from other research modules)
report = ResearchReport(
    title="Strategy Audit - XAUUSD PPO",
    executive_summary="The strategy remains robust despite increased volatility...",
    # ... populate other sections ...
    conclusion="Ready for production deployment with news-event filters."
)

# Export to Markdown
reporter.save_markdown(report, "research_audit_report.md")

# Display in Terminal
reporter.format_for_terminal(report)
```

## Templates

The system uses Jinja2 templates located in `src/research/templates/`. You can customize `research_report.md.j2` to change the layout or styling of the Markdown exports.

## Models

All report sections are defined as structured Pydantic models in `src/research/reporting.py`, ensuring type safety and easy data aggregation from various modules like `RegimeDetector`, `StressLab`, `JournalMiner`, and `BenchmarkEvaluator`.

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
    - **HTML**: Professional browser-viewable reports with:
        - **Interactive TOC**: Anchor links with smooth-scroll navigation.
        - **Dynamic Numbering**: Sequential numbering that adapts to omitted sections.
        - **Visual Progress Bars**: ARIA-compliant visualizations for strategy health scores with dynamic color-coding (Red/Yellow/Green) based on thresholds.
        - **Easy Navigation**: Floating 'Back to Top' button for efficient long-report review.
        - **Accessibility**: Screen-reader optimized table structures and semantic HTML.
    - **Markdown**: Structured, documentation-friendly reports generated via Jinja2 templates with dynamic numbering.
    - **Terminal**: Scannable, interactive dashboards using the `rich` library.

## Usage

### Integration Pattern

Most research and analytics modules implement a `to_report_section()` method that converts their results into a reporting section model.

```python
# Aggregate components
regime_section = regime_detector.generate_summary(data_df)
stress_section = stress_lab.run_scenario(scenario).to_report_section()
pattern_section = journal_miner.run_mining().to_report_section()
drift_section = drift_analyzer.calculate_drift(b_df, c_df).to_report_section()
```

### Generating a Report

```python
from src.research.reporting import ResearchReporter, ResearchReport

# Initialize reporter
reporter = ResearchReporter()

# Create a report object
report = ResearchReport(
    title="Strategy Audit - XAUUSD PPO",
    executive_summary="The strategy remains robust despite increased volatility...",
    regime_analysis=regime_section,
    stress_tests=stress_section,
    trade_patterns=pattern_section,
    model_drift=drift_section,
    # ... other sections ...
    conclusion="Ready for production deployment with news-event filters."
)

# Export to HTML
reporter.save_html(report, "report.html")

# Export to Markdown
reporter.save_markdown(report, "research_audit_report.md")

# Display in Terminal
reporter.format_for_terminal(report)
```

## Templates

The system uses Jinja2 templates located in `src/research/templates/`. You can customize `research_report.md.j2` to change the layout or styling of the Markdown exports.

## Models

All report sections are defined as structured Pydantic models in `src/research/reporting.py`, ensuring type safety and easy data aggregation from various modules like `RegimeDetector`, `StressLab`, `JournalMiner`, and `BenchmarkEvaluator`.

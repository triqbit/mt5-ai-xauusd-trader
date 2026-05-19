# Research Reporting System

The research reporting system is a high-fidelity audit framework designed to provide decision-useful insights for institutional stakeholders, including PMs, Quant Leads, and Auditors.

## Core Features

- **Multi-Format Export:** Supports professional HTML, Markdown, and scannable Terminal (Rich) output.
- **Institutional Metrics:** Calculates and reports advanced quant metrics:
    - Calmar Ratio & Expected Shortfall (CVaR_95)
    - Ulcer Index & Lake Ratio
    - Tail Ratio & SQN
    - Common Sense Ratio (CSR) & Gain-to-Pain Ratio
    - Mathematical Expectancy & Annualized Volatility
    - Recovery Factor & Profit Factor
    - Timing Efficiency & Spread-adjusted Edge Capture
    - Sharpe and Win Rate Decay (Stress Testing)
    - Session Diversification & Flip-Flop Rate (RL Evaluation)
    - Maximum Adverse/Favorable Excursion (MAE/MFE)
- **Automated Risk Triage:** Integrated 'Critical Research Warnings' panel in HTML reports that dynamically highlights FAIL/CRITICAL statuses from stress tests, model drift, and calibration audits.
- **Professional Visualization:**
    - **KPI Dashboard:** High-density visual summaries of core strategy health.
    - **Interactive UX:** Sticky navigation headers with scroll progress indicators, tooltips for institutional metrics, and interactive card hover effects.
    - **Accessibility:** ARIA-hardened accessibility and print-optimized CSS for PDF generation.
- **Modular Architecture:** Pydantic-based data models for extensible research sections covering Regimes, Stress Tests, Hyperopt, Journal Mining (Trade Patterns), Model Drift (PSI), Capital Allocation, Risk & Compliance Auditing, Data Quality Analysis, Benchmarking, RL Evaluation, Rare Event Simulations, Confidence Calibration, Execution Quality, Strategic Confluence, and Audit Methodology.
- **Sectional Scannability:** HTML reports feature top-level 'Summary' status badges for each analytical section (e.g., RESILIENCE: PASS, DRIFT: STABLE, AUDIT: VERIFIED), allowing stakeholders to quickly identify areas of concern.

## Data Models and Constraints

To ensure robust serialization and prevent runtime errors, the reporting system follows strict Pydantic best practices:

- **Field Ordering:** In all research section models (e.g., `StressedMetric`, `SignalMotif`), fields with default values MUST follow all fields without default values. This prevents `PydanticUserError` during model instantiation.
- **Type Safety:** All metrics are strictly typed to ensure consistency across the research pipeline.

## Components

1. **ResearchReporter:** The main engine for template rendering and terminal display. Supports `SectionStatus` Enum for standardized audit levels.
2. **ResearchOrchestrator:** Automates the aggregation of data from various research subsystems (Regime, Stress, Hyperopt, etc.) into a unified report.
3. **Audit Templates:** Professional Jinja2 templates for Markdown and HTML exports.

## Usage

```python
from src.research.reporting import ResearchOrchestrator, ResearchReporter

orchestrator = ResearchOrchestrator(title="Audit", ...)
orchestrator.add_section(stress_test_section)
report = orchestrator.build()

reporter = ResearchReporter()
reporter.format_for_terminal(report)
reporter.save_html(report, "audit.html")
```

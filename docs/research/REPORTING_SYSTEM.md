# Research Reporting System

The research reporting system provides automated generation of institutional-grade strategy summaries in HTML and Markdown formats.

## Key Features

- **Multi-Domain Analysis:** Covers 10 distinct research domains including Regime Analysis, Stress Testing, Model Drift, and Execution Quality.
- **Institutional Metrics:** Calculates advanced metrics such as Tail Ratio, Common Sense Ratio, and Gain-to-Pain Ratio.
- **Professional Visualization:** High-fidelity HTML reports with interactive elements (TOC, back-to-top) and color-coded status indicators.
- **Gold Standard Verification:** Integrated pipeline validation via `scripts/verify_reporting_system.py`.

## Domains Covered

1. **Market Regime Analysis:** Statistical classification of market conditions.
2. **Stress Test Outcomes:** Resilience testing under adversarial scenarios.
3. **Hyperparameter Robustness:** Stability analysis of optimized parameters.
4. **Trade Pattern Findings:** Journal mining for behavioral risks and concentrations.
5. **Model Drift Observations:** Statistical tracking of feature distribution shifts.
6. **Capital Allocation Insights:** Portfolio heat and diversification analytics.
7. **Benchmark Comparisons:** Performance relative to technical and passive baselines.
8. **RL Agent Evaluation:** Specialized DRL agent performance auditing.
9. **Rare Event Simulations:** Resilience against black-swan events (flash crashes, etc.).
10. **Execution Quality:** Alpha decay and slippage analytics.

## Usage

To generate a validation report with mock data:

```bash
PYTHONPATH=. python scripts/verify_reporting_system.py
```

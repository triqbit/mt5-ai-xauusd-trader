# Research Reporting System

The research reporting system provides automated generation of institutional-grade strategy summaries in HTML and Markdown formats.

## Key Features

- **Multi-Domain Analysis:** Covers 10 distinct research domains including Regime Analysis, Stress Testing, Model Drift, and Execution Quality.
- **Institutional Metrics:** Calculates advanced metrics such as Tail Ratio, Common Sense Ratio, and Gain-to-Pain Ratio.
- **Professional Visualization:** High-fidelity HTML reports with interactive elements (TOC, back-to-top) and color-coded status indicators.
- **Gold Standard Verification:** Integrated pipeline validation via `scripts/verify_reporting_system.py`.

## Domains Covered

1. **Market Regime Analysis:** Statistical classification of market conditions.
2. **Stress Test Outcomes:** Institutional-grade resilience testing under adversarial scenarios including choppy breakouts, regime flips, and stale data simulation.
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

## Market Regime Detector

The `RegimeDetector` module (src/models/regime_detector.py) provides advanced market state classification:

- **Regimes:** TRENDING, RANGING, VOLATILE_BREAKOUT, LOW_VOLATILITY_DRIFT, NEWS_SHOCK, and MEAN_REVERSION.
- **Dual Detection Logic:** Uses explainable heuristics and data-driven Gaussian Mixture Models (GMM).
- **Statistical Features:** Kaufman Efficiency Ratio, price slope/angle, z-score, volatility clustering, kurtosis, skewness, and vol-of-vol.
- **Reporting:** Vectorized historical labeling and stability/transition matrices for institutional auditing.

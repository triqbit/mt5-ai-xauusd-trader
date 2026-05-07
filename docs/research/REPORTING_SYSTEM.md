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
4. **Trade Pattern Findings:** Journal mining for behavioral risks, toxic motifs, signal combinations, and attribute concentrations.
5. **Model Drift Observations:** Statistical tracking of feature distribution shifts.
6. **Capital Allocation Insights:** Portfolio heat and diversification analytics.
7. **Benchmark Comparisons:** Performance relative to technical and passive baselines.
8. **RL Agent Evaluation:** Specialized DRL agent performance auditing including stability, turnover, and regime-sensitivity analysis.
9. **Rare Event Simulations:** Resilience against black-swan events (flash crashes, etc.).
10. **Execution Quality:** Alpha decay and slippage analytics.

## Execution Quality Analytics

The `ExecutionAnalyzer` module (src/analytics/execution_quality.py) provides institutional-grade trade quality assessment:

- **Execution Slippage:** Measures the difference between signal request price and actual market fill in pips.
- **Fill Quality:** A sigmoid-based scoring model (0-1) that evaluates execution effectiveness relative to market spread and latency.
- **Timing Efficiency:** Measures entry precision by comparing the fill price to the OHLC range of the execution candle.
- **Edge Capture:** Spread-adjusted measurement of realized edge vs. theoretical strategy edge.
- **Post-Entry Drift (Markouts):** Tracks price movement at fixed horizons (1m, 5m, 15m, 30m, 60m) after entry to distinguish alpha decay from execution drag.
- **Blocked Signal Analysis:** Calculates the opportunity cost of signals rejected by risk management (MFE/MAE and simulated TP/SL outcomes).

## RL Agent Evaluation

The `RLEvaluator` module (src/research/rl_evaluation.py) provides comprehensive performance auditing for reinforcement learning agents:

- **Stability Analysis:** Beyond simple reward, it calculates institutional metrics including Tail Ratio, Common Sense Ratio, Gain-to-Pain Ratio, and System Quality Number (SQN).
- **Regime Stability:** Calculates a stability score based on the consistency of Sharpe ratios across different market regimes (inverse of Coefficient of Variation).
- **Turnover & Policy Health:** Tracks trade frequency, average hold times, and **Action Entropy** to detect policy collapse or excessive stagnation.
- **Reward Decomposition:** Breaks down returns into gross profit, net profit, and commission drag, with concentration analysis on the top 10% of trades.
- **Vectorized Evaluation:** Optimized evaluation loop using pre-calculated regime labels for the entire dataset to ensure high-performance research iterations.
- **Baseline Comparison:** Automated comparison against technical baselines (Momentum, Mean Reversion) and Supervised Learning wrappers.

## Usage

To generate a validation report with mock data for the full system:

```bash
PYTHONPATH=. python scripts/verify_reporting_system.py
```

To verify the journal mining system specifically:

```bash
PYTHONPATH=. python scripts/verify_journal_mining.py
```

## Market Regime Detector

The `RegimeDetector` module (src/models/regime_detector.py) provides advanced market state classification:

- **Regimes:** TRENDING, RANGING, VOLATILE_BREAKOUT, LOW_VOLATILITY_DRIFT, NEWS_SHOCK, and MEAN_REVERSION.
- **Dual Detection Logic:** Uses explainable heuristics and data-driven Gaussian Mixture Models (GMM).
- **Statistical Features:** Kaufman Efficiency Ratio, price slope/angle, z-score, volatility clustering, kurtosis, skewness, and vol-of-vol.
- **Reporting:** Vectorized historical labeling and stability/transition matrices for institutional auditing.

## Dynamic Ensemble System

The `DynamicEnsemble` module (src/models/dynamic_ensemble.py) implements an adaptive weighting engine:

- **Autonomous Tracking:** Independent recording of model predictions and realized market outcomes.
- **Closed-Loop Metrics:** Real-time calculation of accuracy, confidence calibration (alignment between predicted confidence and success), and performance drift.
- **Stability Controls:** EMA-based weight transitions, abrupt swing caps, and oscillation dampening for volatile regimes.
- **Regime Awareness:** Adaptation rates and scoring heuristics are modulated by the current market regime (e.g., NEWS_SHOCK, TRENDING) to ensure robust performance.

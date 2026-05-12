# XAUUSD Strategy Performance & Robustness Audit

---
**Report Metadata**
- **Date:** 2026-05-12 00:19:01.455739+00:00
- **Author:** Jules Research
- **Status:** VERIFIED
- **Scope:** Research and Strategy Audit
---


## Table of Contents
1. [Executive Summary](#executive-summary)

2. [Market Regime Analysis](#2-market-regime-analysis)

3. [Stress Test Outcomes](#3-stress-test-outcomes)

4. [Hyperparameter Robustness](#4-hyperparameter-robustness)

5. [Trade Pattern Findings](#5-trade-pattern-findings-journal-mining)

6. [Model Drift Observations](#6-model-drift-observations)

7. [Capital Allocation Insights](#7-capital-allocation-insights)

8. [Benchmark Comparisons](#8-benchmark-comparisons)





9. [Conclusion & Recommendations](#conclusion--recommendations)

---


## Executive Summary
This report provides a comprehensive evaluation of the AI trading system's performance, resilience, and consistency. Overall, the strategy demonstrates high stability in trending regimes but shows sensitivity to extreme news shocks. Capital allocation is well-diversified, and execution quality remains within institutional standards.

---



## 2. Market Regime Analysis
**Summary:** Market was primarily trending (65%) with high efficiency.

| Regime | Frequency | Avg Duration | Profitability |
|--------|-----------|--------------|---------------|

| Trending | 65.0% | 45 bars | High |

| Ranging | 25.0% | 12 bars | Neutral |

| News Shock | 10.0% | 3 bars | Low |


**Transition Insights:**
Stability: 28.5 bars. Common paths: trending -> ranging (15.5%) | ranging -> news_shock (8.2%)




## 3. Stress Test Outcomes
**Resilience Score:** 88.5/100

| Scenario | Total Return | Max Drawdown | Sharpe | Outcome |
|----------|--------------|--------------|--------|---------|
| **Baseline** | 14.2% | 5.1% | 2.45 | - |

| Spread Widening (3x) | 11.8% | 6.4% | 2.10 | PASS |

| Execution Hell | 8.5% | 9.2% | 1.65 | PASS |

| Flash Crash | -2.1% | 18.5% | -0.45 | FAIL |


**Fragility Indicators:**

- High drawdown sensitivity to price noise > 1.5 sigma

- Latency impact > 500ms degrades alpha capture


**Failure Points:**

- Sudden 2% price gap in < 1 minute

- Service failure during peak London volume





## 4. Hyperparameter Robustness
**Stability Score:** 92.0/100

| Parameter | Range Tested | Optimal Value | Sensitivity |
|-----------|--------------|---------------|-------------|

| fast_ema_window | 5-25 | 12 | Low |

| confidence_threshold | 0.5-0.9 | 0.65 | Medium |

| volatility_lookback | 10-50 | 20 | Low |


**Optimization Insights:**
OOS Sharpe Mean: 2.15 | WFE: 0.88 | Worst OOS Sharpe: 1.45 | IS-OOS Gap: 0.25




## 5. Trade Pattern Findings (Journal Mining)
**Key Insight:** Critical behavioral risks identified: Overtrading during NY session.

### Profitable Concentrations
| Attribute | Value | Win Rate | Profit Factor |
|-----------|-------|----------|---------------|

| algo_session | Ensemble @ London | 62.0% | 2.45 |

| algo_volatility | Ensemble @ Normal Vol | 58.0% | 2.1 |




### Behavioral Risks

- **Overtrading:** High trade frequency detected in NY session (4.2 trades/hour).

- **Loss Clustering:** Detected 2 clusters of 5+ losses during FOMC news shocks.





## 6. Model Drift Observations
| Metric | Baseline | Current | Drift | Status |
|--------|----------|---------|-------|--------|

| Target Distribution: close | 2345.50 | 2342.10 | 2.4% | STABLE |

| Return Volatility | 0.0012 | 0.0018 | 25.0% | WARNING |


**Feature Importance Shifts:**
Significant shifts in: atr_ratio (+0.45), z_score (-0.32), vol_of_vol (+0.18)




## 7. Capital Allocation Insights
**Portfolio Heat:** 42.5% | **Diversification Score:** 0.85

| Symbol/Family | Allocated | Heat | Performance Multiplier |
|---------------|-----------|------|------------------------|

| ENSEMBLE_XAUUSD_M5 | $42,500.00 | 42.5% | 1.15 |

| PPO_XAUUSD_M15 | $0.00 | 0.0% | 0.85 |


**Rejection Summary:**

- TOTAL_HEAT_LIMIT: 0 occurrences

- SYMBOL_CONCENTRATION_LIMIT: 2 occurrences





## 8. Benchmark Comparisons
| Strategy | Total Return | Sharpe | MaxDD | PF | SQN | Recov | P-Value |
|----------|--------------|--------|-------|----|-----|-------|---------|

| EMA_Crossover | 8.5% | 1.20 | 12.4% | 1.45 | 0.00 | 0.00 | 0.0012 |

| Momentum_ROC | 6.2% | 0.95 | 15.8% | 1.25 | 0.00 | 0.00 | 0.0001 |


**Statistical Significance:**
Compared 2 strategies against Ensemble. 2 showed outperformance.










---
## Conclusion & Recommendations
**Strategic Conclusion:**
The strategy is suitable for deployment in production with a 'Verified' status, provided macro guardrails are active.


**Actionable Recommendations:**

- Reduce risk multiplier during high-impact news windows.

- Recalibrate LSTM confidence thresholds every 30 days.

- Increase capital allocation to the London-NY session crossover.

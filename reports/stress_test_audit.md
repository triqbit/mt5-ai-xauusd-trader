# Institutional Resilience Audit: EMA Crossover Strategy

---
**Report Metadata**
- **Date:** 2026-05-12 05:48:06.756207+00:00
- **Author:** Jules Research
- **Status:** PROVISIONAL
- **Scope:** Research and Strategy Audit
---


## Table of Contents
1. [Executive Summary](#executive-summary)


2. [Stress Test Outcomes](#2-stress-test-outcomes)







3. [Rare Event Simulations](#3-rare-event-simulations)



4. [Conclusion & Recommendations](#conclusion--recommendations)

---


## Executive Summary
This audit evaluates the EMA_Crossover_10_30 strategy under adversarial conditions. The stress laboratory simulates execution friction, data instability, and regime shifts to identify non-linear failure points and quantify strategy fragility.

---





## 2. Stress Test Outcomes
**Resilience Score:** 29.43080955722126/100

| Scenario | Total Return | Max Drawdown | Sharpe | Outcome |
|----------|--------------|--------------|--------|---------|
| **Baseline** | -1.74% | 5.16% | -0.19 | - |

| Execution Hell | -34.00% | 35.20% | -0.80 | FAIL |

| Liquidity Crisis | -1.43% | 9.53% | 0.03 | FAIL |

| Regime Shock | -149.79% | 148.40% | 0.18 | FAIL |

| Flash Crash | -134.85% | 137.68% | -0.90 | FAIL |


**Fragility Indicators:**

- Drawdown explosion in Execution Hell

- Sharpe ratio halved under Execution Hell

- Drawdown explosion in Regime Shock

- Drawdown explosion in Flash Crash

- Sharpe ratio halved under Flash Crash

- Extreme slippage sensitivity in Flash Crash


**Failure Points:**

- Critical drawdown (>50%) in Regime Shock

- Critical drawdown (>50%) in Flash Crash

















## 3. Rare Event Simulations
**Insights:** Evaluated 1 rare event scenarios. Detected 0 high-impact events (>5% deviation). All events remained within manageable risk bounds.

| Event Type | Peak Impact | Realized Vol | Recovery |
|------------|-------------|--------------|----------|

| news_shock | 4.67% | 0.0232 | 0.0% |







---
## Conclusion & Recommendations
**Strategic Conclusion:**
The strategy achieved a resilience score of 29.4. While it handles moderate spread widening, it shows critical fragility during flash crashes and high-latency environments.

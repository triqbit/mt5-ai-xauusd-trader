# Advanced Risk Controls & Defensive Safeguards

This document describes the institutional-grade safety controls implemented in the `RiskManager` to protect capital during unstable market conditions and ensure model reliability.

## 1. Extreme Volatility Circuit Breaker

The system implements a mandatory execution halt when market volatility reaches anomalous levels.

- **Mechanism:** Compares the 14-period Average True Range (ATR) to its 30-day moving average (8,640 bars on M5).
- **Threshold:** If the current ATR Ratio exceeds **3.0x**, all new trade entries are strictly prohibited.
- **Rationale:** Protects against flash crashes, news-driven spikes, and liquidity vacuums where slippage and spread widening make trading mathematically unfavorable.

## 2. Regime-Adaptive Confidence Floors

Trading signals must meet varying confidence requirements based on the detected market regime. This ensures that the system is more conservative during high-entropy or unstable environments.

| Market Regime | Confidence Floor | Description |
|---------------|------------------|-------------|
| **NEWS_SHOCK** | 0.80 (80%) | Highest bar; requires extreme model certainty during shocks. |
| **VOLATILE_BREAKOUT** | 0.70 (70%) | Elevated bar for high-velocity momentum shifts. |
| **MEAN_REVERSION** | 0.65 (65%) | Stricter requirement for counter-trend positions. |
| **LOW_VOLATILITY_DRIFT** | 0.60 (60%) | Slightly higher bar for slow-moving, low-volatility trends. |
| **TRENDING / RANGING** | 0.55 (55%) | Standard institutional confidence requirement. |

## 3. Position Sizing Multipliers

Position sizes are dynamically scaled based on both model confidence and market volatility, acting as a "soft" safeguard before hard limits are hit.

### 3.1 Confidence Scaling
- **Low Confidence (< 0.55):** Trade skipped.
- **Medium Confidence (0.55 - 0.65):** 50% Position Size.
- **High Confidence (>= 0.65):** 100% Position Size.

### 3.2 Volatility Scaling
- **Normal Volatility (< 1.5x):** 100% Position Size.
- **High Volatility (1.5x - 2.0x):** 75% Position Size.
- **Very High Volatility (2.0x - 3.0x):** 50% Position Size.
- **Extreme Volatility (> 3.0x):** 0% (Halt).

## 4. Audit Traceability

Every evaluation of these safety layers is recorded in the `AuditedRiskManager`. Rejections due to the volatility breaker or regime safety checks are explicitly logged with their respective triggers, enabling post-trade forensics and performance attribution.

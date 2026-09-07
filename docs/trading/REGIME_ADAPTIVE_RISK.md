# Regime-Adaptive Risk Guardrails

## Overview
The system now implements regime-adaptive safety guardrails in the `RiskManager`. This enhancement allows the risk engine to dynamically tighten model health thresholds based on the detected market state, providing an extra layer of protection during unstable market conditions.

## Adaptive Thresholds
The following adjustments are applied based on the `MarketRegime`:

| Regime | Adjustments |
| :--- | :--- |
| `NEWS_SHOCK` | Drift threshold reduced by 50%, Accuracy floor increased by 5% |
| `VOLATILE_BREAKOUT` | Drift threshold reduced by 25% |
| `MEAN_REVERSION` | Calibration error threshold reduced by 40% |

## Configuration
The drawdown circuit breaker is now configurable via the `max_drawdown` parameter in `TradingConfig` (defaults to 0.15).

## Traceability
Regime-adaptive decisions are fully logged to the audit trail via `AuditedRiskManager`.

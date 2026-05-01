# Acceptance Criteria: StressLab (Strategy Resilience Testing)

## Overview
StressLab is an adversarial testing framework designed to evaluate the robustness of XAUUSD trading strategies beyond normal market conditions. It simulates various execution, data, and market structure hurdles to identify strategy fragility.

## 1. Adverse Condition Replay
- [x] **Spread Widening:** Must support multipliers on base spreads to simulate low-liquidity periods.
- [x] **Slippage Spikes:** Must inject basis-point slippage on entries and exits.
- [x] **Missing Ticks:** Must support probabilistic dropping of OHLCV bars.
- [x] **Delayed Fills:** Must support N-step execution delays to simulate latency.
- [x] **Choppy Fake Breakouts:** Must inject synthetic price spikes followed by immediate reversals.
- [x] **Regime Transitions:** Must simulate sudden trend flips or volatility shocks.
- [x] **Service Degradation:** Must support probabilistic blocking of signals (connectivity simulation).

## 2. Reporting & Analytics
- [x] **Typed Metrics:** All results must be captured in `StressTestMetrics` Pydantic models.
- [x] **Resilience Score:** A composite 0-100 score indicating performance retention under stress.
- [x] **Fragility Indicators:** Automated detection of drawdown inflation or Sharpe ratio decay.
- [x] **Failure Points:** Identification of specific scenarios where a strategy becomes unprofitable.

## 3. Implementation Standards
- [x] **Type Safety:** Full Pydantic v2 usage for configuration and reports.
- [x] **Reproducibility:** Seeded random number generation for deterministic stress runs.
- [x] **Candle Consistency:** Recalculates high/low values after price perturbations to maintain OHLC integrity.
- [x] **Compliance:** Adheres to Python 3.11+ UTC timestamp standards.

## 4. Test Coverage
- [x] **Unit Tests:** Verified perturbations, backtest logic, and report generation in `tests/test_stress_lab.py`.
- [x] **E2E Compatibility:** Integrated with synthetic data generators and existing strategy protocols.

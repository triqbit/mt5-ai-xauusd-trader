# Synthetic Test Scenarios

This document describes the synthetic data generators and deterministic scenarios available for testing the trading system's safety and resilience.

## Overview

The `src/utils/synthetic_data.py` module provides tools to generate realistic market data and validation scenarios. These are used to verify that the `ExecutionFilter` and `RiskManager` behave correctly under various conditions.

## Scenario Generators

### 1. ScenarioGenerator (OHLCV Data)

Generates deterministic synthetic price action.

-   **Regimes**: `trending`, `ranging`, `volatile`, `gapping`, `whipsaw`, `flash_crash`, `regime_shift`.
-   **Data Quality Anomalies**:
    -   `generate_with_holes()`: Injects NaNs into the data to test missing-data resilience.
    -   `generate_stale_feed()`: Simulates a frozen price feed by repeating bars.

### 2. ExecutionScenarioBuilder (Validation Scenarios)

Bundles `TradeSignal`, `pd.DataFrame`, and other context into a `ValidationScenario` object for easy testing of the `ExecutionFilter`.

-   **Passing Scenarios**: `passing_buy`.
-   **Technical Failures**: `atr_failure`, `trend_failure`, `ema_out_of_sequence`, `momentum_failure`.
-   **Risk & Compliance Failures**:
    -   `session_violation`: Signals generated during market close (weekends).
    -   `drawdown_breach`: Signals generated when the account exceeds drawdown limits.
    -   `confidence_failure`: Signals with low model confidence.
    -   `performance_floor_failure`: Signals when historical win rate is below the floor.
-   **Stateful Failures**:
    -   `flicker_sequence`: A series of alternating signals to trigger the `Signal Consistency` (Flicker Guard) layer.

## Usage Example

```python
from src.utils.synthetic_data import ExecutionScenarioBuilder
from src.trading.execution_filter import ExecutionFilter

builder = ExecutionScenarioBuilder(seed=42)
scenario = builder.drawdown_breach()

filter_svc = ExecutionFilter()
decision = filter_svc.validate(
    scenario.signal,
    scenario.market_data,
    current_drawdown=scenario.current_drawdown
)

assert decision.is_approved is False
assert decision.blocked_by == "DRAWDOWN_LIMIT"
```

## Maintenance

When adding new layers to the `ExecutionFilter` cascade, ensure a corresponding scenario is added to the `ExecutionScenarioBuilder` and documented here.

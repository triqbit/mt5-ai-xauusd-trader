# Synthetic Test Scenarios

This document outlines the synthetic scenario builders available in `src/utils/synthetic_data.py` for testing the trading system's resilience and decision-making under various conditions.

## MacroScenarioBuilder

The `MacroScenarioBuilder` provides deterministic macroeconomic events and risk states.

### Key Scenarios
- **NFP Shock**: Simulates a High-Impact Non-Farm Payrolls release.
- **FOMC Policy Day**: Generates critical FOMC statements and interest rate decisions.
- **Geopolitical Tension**: Creates ongoing crises with extended durations and potential execution blocks.
- **CPI Cluster**: Simulates a sequence of inflation-related data releases.

### Usage
```python
from src.utils.synthetic_data import MacroScenarioBuilder
builder = MacroScenarioBuilder(seed=42)
events = builder.fomc_policy_day()
risk_status = builder.extreme_risk_status(reason="FOMC Decision Pending")
```

## SystemContextBuilder

The `SystemContextBuilder` is a high-level orchestrator that composes multiple dimensions of the system state into a unified `SystemScenarioContext`.

### Features
- **Crisis Scenario**: A high-volatility flash crash occurring during a geopolitical crisis, with degraded model health. Useful for testing risk rejections.
- **Bull Run Scenario**: A steady trending market with clear macro conditions and perfect model health. Useful for verifying successful execution paths.

### Usage
```python
from src.utils.synthetic_data import SystemContextBuilder
builder = SystemContextBuilder(seed=42)
context = builder.create_crisis_scenario()

# Access integrated components
df = context.ohlcv
signal = context.signal
risk = context.macro_risk
health = context.model_health
```

## Determinism
All builders support an optional `seed` parameter to ensure that test data remains consistent across CI runs and different environments.

# Rare Event Simulator

## Overview
The `RareEventSimulator` is an institutional-grade tool designed to generate synthetic market data representing rare but plausible "black-swan" events for XAUUSD. It extends standard historical backtesting by injecting adversarial price and execution conditions that are not sufficiently represented in historical datasets.

## Supported Scenarios
- **Flash Crash**: Rapid price collapse with partial/full recovery and volume surges.
- **Liquidity Vacuum**: Erratic price jumps, significant spread widening, and extreme volume dry-ups.
- **Gold Gap**: Discontinuous price jumps with follow-through volatility.
- **Violent Reversal**: Strong trend followed by an abrupt, high-magnitude reversal.
- **Dislocation**: Sudden price shift followed by a permanent regime change in volatility and drift.
- **Volatility Cluster**: Abnormal clusters of high volatility driven by multiple decaying GARCH-like shocks.
- **Multi-Session Dislocation**: A sequence of regime shifts across multiple trading sessions to test long-term strategy adaptability.
- **News Shock**: Violent directional moves followed by sustained high volatility, calibrated to trigger institutional regime detection thresholds.
- **Fat Finger**: Extreme single-tick outlier wicks with immediate recovery and spread widening to test stop-loss resilience.
- **Bull/Bear Trap**: Fake breakouts past consolidation ranges followed by violent reversals to test trend-following strategy robustness.

## Key Features
- **Standardized Metrics**: `peak_impact_pct` represents the maximum percentage price deviation from the event start, providing a consistent measure across all scenario types.
- **Configurable Data Frequency**: Supports arbitrary timeframes (e.g., M1, M5, H1) via the `bars_per_day` configuration, adjusting dummy timestamps and realized volatility annualization accordingly.
- **Asset Generality**: High/low price expansion in scenarios like `Liquidity Vacuum` is volatility-relative, making the simulator suitable for various assets beyond XAUUSD.
- **Spread Support**: Generates a high-fidelity `spread` column, essential for realistic execution stress testing in `StressLab`.
- **Configurable Severity**: All scenarios are scaled by an `event_magnitude` parameter.
- **Suite Generation**: The `generate_suite()` method produces a standardized set of adversarial scenarios for bulk resilience auditing.
- **Reproducibility**: Uses `numpy.random.default_rng` with optional seeds for deterministic scenario generation.

## Integration
The simulator integrates seamlessly with the following components:
- **Feature Engineering**: Synthetic DataFrames contain standard OHLCV+Spread columns compatible with `FeatureEngineer`.
- **Stress Lab**: Provides high-adversity price action for evaluating strategy fragility.
- **Research Reporting**: `RareEventResult` objects map directly to the `RareEventSection` in institutional research reports.

## Usage Example
```python
from src.research.rare_event_simulator import RareEventSimulator, RareEventConfig, RareEventType

simulator = RareEventSimulator(seed=42)
config = RareEventConfig(event_type=RareEventType.FLASH_CRASH, event_magnitude=2.0)
df, result = simulator.generate_scenario(config)

# Generate a full audit suite
suite = simulator.generate_suite(n_steps=1000)
```

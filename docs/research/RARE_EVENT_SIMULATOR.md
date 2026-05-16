# Rare Event Simulator

The `RareEventSimulator` (src/research/rare_event_simulator.py) generates synthetic OHLCV data for rare but plausible market situations that are often under-represented in historical datasets.

## Purpose

The primary goal of the simulator is to enable serious rare-event strategy research and black-swan resilience testing. By generating adversarial market conditions, it allows quant researchers to identify non-linear failure points in their trading strategies.

## Key Features

- **Plausible Scenarios**: Generates flash crashes, liquidity vacuums, gold gaps, and more using scientifically grounded models (Merton Jump-Diffusion, GARCH).
- **Scenario Chaining**: Supports linking multiple rare events into a single, continuous OHLCV price path with guaranteed price and date continuity.
- **Pipeline Compatible**: Produces DataFrames with standardized lowercase columns (`open`, `high`, `low`, `close`, `tick_volume`, `real_volume`, `spread`). Uses strict `float32` for prices and `int64` for volumes to match `FeatureEngineer` expectations.
- **Numerical Stability**: Implements explicit casting for all DataFrame modifications to avoid pandas `FutureWarning` issues and ensure numerical consistency during high-fidelity simulations.
- **Configurable**: Supports adjusting magnitude, duration, recovery factor, and frequency (bars per day).
- **Reproducible**: Uses `numpy` random generators with optional seeds for deterministic scenario generation.

## Supported Scenarios

1.  **Flash Crash**: Rapid price collapse followed by a quick partial or full recovery, accompanied by a volume surge. Calibrated to trigger institutional volatility regimes (ATR Ratio > 2.0).
2.  **Liquidity Vacuum**: Period of erratic price jumps, extreme spreads, and significantly dropped volume.
3.  **Gold Gap**: Discontinuous price jumps (bullish or bearish) with follow-through volatility.
4.  **Violent Reversal**: A strong trend followed by an abrupt, high-magnitude reversal.
5.  **Dislocation**: A sudden price shift leading into a completely different market regime (higher volatility, different drift).
6.  **Volatility Cluster**: An abnormal cluster of high volatility with multiple decaying shocks, approximated using GARCH(1,1) logic.
7.  **Multi-Session Dislocation**: A sequence of regime shifts across multiple sessions, testing a strategy's multi-day adaptability.
8.  **News Shock**: A violent directional move followed by sustained high volatility and erratic behavior. Calibrated to trigger the `NEWS_SHOCK` regime in the `RegimeDetector` (ER > 0.7, ATR Ratio > 2.0).
9.  **Short Squeeze**: Rapid parabolic move up driven by buy-side liquidation, followed by a blow-off top. Tests resistance-breakout and stop-loss hunting logic.
10. **Cascade Liquidation**: A series of accelerating downward price shocks (margin calls). Tests trailing-stop and capital preservation logic under extreme stress.
11. **Mean Reversion Failure**: An overextended move without significant pullbacks, testing strategy discipline during persistent grinds.
12. **Silent Trend**: A persistent, low-volatility trend that steadily moves away from entry points without triggering volatility alerts.

## Configuration

The `RareEventConfig` model includes the following parameters:

- `event_type`: Type of rare event to simulate.
- `n_steps`: Total number of bars in the generated series (min 100).
- `start_price`: Starting price for the simulation (default 2300.0).
- `base_volatility`: Baseline volatility for normal periods.
- `drift`: Base daily-equivalent drift.
- `base_volume`: Average tick volume during normal periods.
- `event_magnitude`: Multiplier for the severity of the event.
- `recovery_factor`: Proportion of the event's impact that is eventually recovered.
- `recovery_bars`: Number of bars taken for the market to stabilize after the event peak.
- `bars_per_day`: Number of bars per trading day (defines frequency).
- `start_date`: Base date for the generated time index.
- `seed`: Random seed for reproducibility.

## Usage Example

### Single Scenario
```python
from src.research.rare_event_simulator import RareEventSimulator, RareEventConfig, RareEventType

simulator = RareEventSimulator(seed=42)
config = RareEventConfig(
    event_type=RareEventType.FLASH_CRASH,
    n_steps=500,
    event_magnitude=2.0,
    start_date="2024-05-01"
)

df, result = simulator.generate_scenario(config)
print(df.head())
print(f"Peak Impact: {result.peak_impact_pct:.2%}")
print(f"Description: {result.description}")
```

### Chained Scenarios
```python
configs = [
    RareEventConfig(event_type=RareEventType.FLASH_CRASH, n_steps=200),
    RareEventConfig(event_type=RareEventType.GOLD_GAP, n_steps=100),
    RareEventConfig(event_type=RareEventType.NEWS_SHOCK, n_steps=200),
]

# Generates a continuous 500-bar DataFrame containing all three events
combined_df, results = simulator.chain_scenarios(configs)
```

## Suite Generation and Reporting

For comprehensive testing, you can generate a suite of all supported rare events and aggregate them into a report section:

```python
# Generate a full suite of scenarios
suite = simulator.generate_suite(n_steps=500, magnitude=1.5)

# Convert to a reporting section for ResearchReporter
report_section = simulator.generate_report_section(suite)
print(report_section.insights)
```

## Integration

The generated DataFrames can be passed directly to the `FeatureEngineer` or used as synthetic environments for RL agent evaluation:

```python
from src.core.feature_engineering import FeatureEngineer

fe = FeatureEngineer()
features_df = fe.compute_features(df)
```

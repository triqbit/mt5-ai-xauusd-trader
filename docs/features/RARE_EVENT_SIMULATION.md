# Rare Event Simulation

## Overview
The `RareEventSimulator` is a specialized research component designed to generate synthetic market data representing rare but plausible 'black-swan' events for XAUUSD. This allows for rigorous resilience testing of trading strategies beyond the limitations of historical data.

## Supported Scenarios
- **Flash Crash**: Rapid price collapse followed by partial or full recovery.
- **Liquidity Vacuum**: Periods of extreme volatility, erratic price jumps, and low volume.
- **Gold Gap**: Discontinuous price jumps (e.g., news-driven or weekend gaps).
- **Violent Reversal**: A strong trend followed by an abrupt, high-velocity reversal.
- **Dislocation**: A multi-session breakdown or shift in price levels and volatility regimes.
- **Volatility Cluster**: Abnormal clusters of sustained high volatility (GARCH-like crisis mode).

## Usage
The simulator uses Pydantic models for configuration, ensuring type safety and easy integration into research pipelines.

```python
from src.research.rare_event_simulator import RareEventSimulator, RareEventConfig, RareEventType

simulator = RareEventSimulator(seed=42)
config = RareEventConfig(
    event_type=RareEventType.FLASH_CRASH,
    n_steps=500,
    start_price=2350.0,
    event_magnitude=1.5
)

df = simulator.generate_scenario(config)
```

## Resilience Testing Integration
The output is a standard OHLCV DataFrame compatible with the `StressLab` and other evaluation components, enabling automated black-swan resilience scoring for all strategies.

# Synthetic Data & Risk Scenarios

This document outlines the synthetic data generation and risk scenario building tools available for testing the MT5 AI/ML Trading Bot.

## ScenarioGenerator

Located in `src/utils/synthetic_data.py`, the `ScenarioGenerator` provides deterministic OHLCV data for various market regimes.

### Supported Regimes

- **trending**: Price follows a constant trend with normal noise.
- **ranging**: Mean-reverting price action around a starting value.
- **volatile**: Price with frequent high-variance spikes.
- **gapping**: Price with occasional large percentage gaps (2%).
- **whipsaw** (New): A bullish breakout followed by an immediate, sharp bearish reversal. Useful for testing trailing stop resilience and "fake-out" detection.
- **stale** (New): Frozen price action (zero returns). Useful for testing system behavior during low liquidity or data feed freezes.
- **malformed**: Data with intentional errors (NaNs, negative prices, High < Low) to test pipeline resilience.

## RiskScenarioBuilder

Located in `src/utils/synthetic_data.py`, the `RiskScenarioBuilder` generates deterministic sequences of `TradeSignal` objects.

### Key Methods

- **consecutive_losses(n_signals, symbol, start_price)**:
  Generates `n_signals` that are likely to result in losses. This is critical for testing:
  - Daily loss limits
  - Circuit breakers (drawdown halts)
  - Consecutive loss counters

- **ensemble_dissent(symbol, price)**:
  Generates a list of signals representing conflicting model votes (e.g., PPO BUY vs. LSTM SELL). This tests:
  - Ensemble voting logic
  - Signal validation gate behavior under high uncertainty

## Usage in Tests

These tools are designed to make tests deterministic and broad. See `tests/test_risk_scenarios.py` and `tests/test_synthetic_data.py` for implementation examples.

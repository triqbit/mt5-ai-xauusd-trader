# Synthetic Data & Risk Scenarios

This document outlines the synthetic data generation and risk scenario building tools available for testing the MT5 AI/ML Trading Bot.

## ScenarioGenerator

Located in `src/utils/synthetic_data.py`, the `ScenarioGenerator` provides deterministic OHLCV data for various market regimes.

### Supported Regimes

- **trending**: Price follows a constant trend with normal noise.
- **ranging**: Mean-reverting price action around a starting value.
- **volatile**: Price with frequent high-variance spikes.
- **gapping**: Price with occasional large percentage gaps (2%).
- **whipsaw**: A bullish breakout followed by an immediate, sharp bearish reversal. Useful for testing trailing stop resilience and "fake-out" detection.
- **stale**: Frozen price action (zero returns). Useful for testing system behavior during low liquidity or data feed freezes.
- **flash_crash**: Extreme drop followed by partial recovery. Essential for validating circuit breaker response and emergency halt triggers.
- **regime_shift**: Transition from a stable/ranging regime to a highly volatile one. Used for testing model adaptability and risk multiplier adjustments.
- **mean_reversion**: Oscillating price process with high z-score and low efficiency ratio.
- **low_volatility_drift**: Small constant trend with minimal noise and low ATR.
- **news_shock**: Extreme spike at the end to trigger news-like volatility checks.
- **noisy**: Ranging data with frequent extreme outliers (spikes).
- **missing_data**: Data with random NaN "holes" in OHLCV columns to test pipeline robustness.
- **malformed**: Data with intentional errors (NaNs, negative prices, High < Low) to test pipeline resilience.

## BacktestScenarioBuilder

Located in `src/utils/synthetic_data.py`, the `BacktestScenarioBuilder` provides deterministic price sequences designed to verify the mathematical correctness of the `BacktestEngine`.

### Key Methods

- **drawdown_recovery(n_steps, start_price)**: Creates a 10% drawdown followed by a 20% gain. Used to verify `max_drawdown` and `recovery_factor` calculations.
- **wick_traps(n_steps, start_price)**: Creates bars where both SL and TP levels are touched. Verifies the conservative "SL-first" exit policy.
- **steady_sharpe(n_steps, start_price)**: Near-perfect linear trend with minimal noise to produce high Sharpe and Profit Factor for baseline testing.

## ExecutionScenarioBuilder

Located in `src/utils/synthetic_data.py`, the `ExecutionScenarioBuilder` generates paired `TradeSignal` and `pd.DataFrame` (market data) designed to test specific layers of the `ExecutionFilter`.

### Key Scenarios

- **passing_buy**: A clean BUY signal in a moderate bullish trend that satisfies all filter layers.
- **atr_failure**: A scenario with an extreme volatility spike designed to trigger the ATR Volatility filter.
- **trend_failure**: A BUY signal generated during a bearish trend, designed to trigger the Trend Angle filter.
- **ema_out_of_sequence**: A scenario where EMAs are not correctly stacked (e.g., EMA8 < EMA21 for BUY), designed to trigger the EMA Sequence filter.
- **momentum_failure**: A scenario where RSI is in an overbought zone, designed to trigger the Momentum filter.
- **session_violation**: BUY signal on a Saturday (market closed).
- **drawdown_violation**: Signal with excessive drawdown (e.g., 0.15) to trigger risk halts.
- **confidence_violation**: Signal with confidence below threshold (0.4) to trigger rejection.
- **signal_flicker_violation**: A sequence of oscillating signals (BUY, SELL, BUY, SELL, ...) to trigger Flicker Guard.
- **performance_violation**: Signal with a mocked trade logger reporting low win rate to trigger Performance Floor.

## RegimeScenarioBuilder

Located in `src/utils/synthetic_data.py`, the `RegimeScenarioBuilder` generates deterministic datasets specifically designed to trigger each `MarketRegime` label in the `RegimeDetector`.

### Key Methods

- **trending()**: Triggers `MarketRegime.TRENDING`.
- **ranging()**: Triggers `MarketRegime.RANGING`.
- **mean_reversion()**: Triggers `MarketRegime.MEAN_REVERSION`.
- **volatile_breakout()**: Triggers `MarketRegime.VOLATILE_BREAKOUT`.
- **low_volatility_drift()**: Triggers `MarketRegime.LOW_VOLATILITY_DRIFT`.
- **news_shock()**: Triggers `MarketRegime.NEWS_SHOCK`.

## ModelHealthGenerator

Located in `src/utils/synthetic_data.py`, the `ModelHealthGenerator` provides deterministic model health metrics for testing stability guards.

### Supported States

- **perfect_health**: Metrics well within safety limits.
- **degraded_drift**: Breaches the model drift threshold.
- **degraded_accuracy**: Breaches the model accuracy floor.
- **degraded_calibration**: Breaches the model calibration threshold.

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

- **daily_loss_breach(symbol, price, n_losses)** (New):
  Generates a sequence of high-impact losing signals. Used to verify that the `RiskManager` correctly halts trading after the daily loss percentage floor is hit.

- **drawdown_circuit_breaker(symbol, price)** (New):
  Generates an extreme losing scenario designed to trigger the system-wide 15% drawdown circuit breaker, ensuring all execution is blocked until manual intervention.

## MacroScenarioBuilder

Located in `src/utils/synthetic_data.py`, the `MacroScenarioBuilder` generates deterministic `MacroEvent` objects for risk testing.

### Key Scenarios

- **nfp_shock**: High impact Non-Farm Payrolls event.
- **fomc_meeting**: Critical impact FOMC Rate Decision event.
- **geopolitical_crisis**: High impact geopolitical tension event.

## SystemContextBuilder

Located in `src/utils/synthetic_data.py`, the `SystemContextBuilder` generates integrated test contexts combining price action, macro events, and risk status.

### Key Contexts

- **normal_trading**: Context for standard, low-risk trading.
- **high_impact_macro_event**: Context during a High-Impact news release (NFP), including a defensive `RiskStatus`.
- **extreme_volatility_with_risk_block**: Context with extreme price action (Flash Crash) and a defensive `RiskStatus` (FOMC news block).

## Usage in Tests

These tools are designed to make tests deterministic and broad. See `tests/test_risk_scenarios.py` and `tests/test_synthetic_data.py` for implementation examples.

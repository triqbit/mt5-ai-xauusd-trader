# Synthetic Data & Risk Scenarios

This document outlines the synthetic data generation and risk scenario building tools available for testing the MT5 AI/ML Trading Bot.

## ScenarioGenerator

Located in , the  provides deterministic OHLCV data for various market regimes.

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

### Advanced Generation Features

- **generate_multi_timeframe(n_steps_base, base_freq, timeframes, regime)**: Generates consistent OHLC data across multiple timeframes (e.g., M1, M5, H1) via resampling. This ensures that the high-TF "High" is the maximum of the underlying low-TF bars, and "Open" prices align correctly across scales.
- **inject_faults(df, fault_type, prob)**: Injects operational hazards into an existing dataset:
    - **stale**: Simulates a frozen data feed where prices don't change.
    - **outliers**: Ghost ticks or extreme price spikes (e.g., bad feed).
    - **zero_volume**: Price moves but volume is reported as zero.
    - **gaps**: Price jumps without continuity (slippage or weekend gaps).
    - **high_spread**: Simulates extreme spread spikes (e.g., news or rollover) to test spread-related risk limits and halts.
- **Price Continuity**: The generator ensures price continuity for standard regimes, providing realistic price action for backtesting.
- **Spread & Volume**: Generates movement-correlated `tick_volume` and deterministic `spread_pips` to support realistic technical analysis and spread-risk validation.

## LifecycleScenarioBuilder

Located in `src/utils/synthetic_data.py`, this builder creates multi-stage deterministic price and event sequences to test the system's operational lifecycle and state machine transitions.

### Key Scenarios

- **flash_crash_recovery_cycle(n_steps)**: Simulates a full cycle of Normal Ranging -> Flash Crash -> Circuit Breaker -> Stabilization -> Recovery. Essential for end-to-end resilience testing.
- **news_block_lifecycle(n_steps)**: Simulates Ranging -> High Impact News (Macro Event) -> News Shock Price Action -> Post-news stabilization.

## ExecutionQualityScenarioBuilder

Located in `src/utils/synthetic_data.py`, this builder generates deterministic sets of historical trade data for performance testing. Useful for verifying win rate guards, slippage alerts, and execution cost analysis.

### Key Scenarios

- **toxic_flow_sequence(n_trades)**: Generates trades with consistently high negative slippage and a low win rate (approx 20%). Used to verify that `Performance Guard` correctly halts trading.
- **high_performance_sequence(n_trades)**: Generates trades with a high win rate (approx 70%) and positive edge capture (low slippage).
- **edge_case_fills()**: Specific scenarios including perfect fills (zero slippage), extreme slippage spikes, and break-even trades.

## BacktestScenarioBuilder

Located in , the  provides deterministic price sequences designed to verify the mathematical correctness of the .

### Key Methods

- **drawdown_recovery(n_steps, start_price)**: Creates a 10% drawdown followed by a 20% gain. Used to verify  and  calculations.
- **wick_traps(n_steps, start_price)**: Creates bars where both SL and TP levels are touched. Verifies the conservative "SL-first" exit policy.
- **steady_sharpe(n_steps, start_price)**: Near-perfect linear trend with minimal noise to produce high Sharpe and Profit Factor for baseline testing.

## ExecutionScenarioBuilder

Located in , the  generates paired  and  (market data) designed to test specific layers of the .

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

Located in , the  generates deterministic datasets specifically designed to trigger each  label in the .

### Key Methods

- **trending()**: Triggers .
- **ranging()**: Triggers .
- **mean_reversion()**: Triggers .
- **volatile_breakout()**: Triggers .
- **low_volatility_drift()**: Triggers .
- **news_shock()**: Triggers .

## ModelHealthGenerator

Located in , the  provides deterministic model health metrics for testing stability guards.

### Supported States

- **perfect_health**: Metrics well within safety limits.
- **degraded_drift**: Breaches the model drift threshold.
- **degraded_accuracy**: Breaches the model accuracy floor.
- **degraded_calibration**: Breaches the model calibration threshold.

## RiskScenarioBuilder

Located in , the  generates deterministic sequences of  objects.

### Key Methods

- **consecutive_losses(n_signals, symbol, start_price)**:
  Generates  that are likely to result in losses. This is critical for testing:
  - Daily loss limits
  - Circuit breakers (drawdown halts)
  - Consecutive loss counters

- **ensemble_dissent(symbol, price)**:
  Generates a list of signals representing conflicting model votes (e.g., PPO BUY vs. LSTM SELL). This tests:
  - Ensemble voting logic
  - Signal validation gate behavior under high uncertainty

- **daily_loss_breach(symbol, price, n_losses)** (New):
  Generates a sequence of high-impact losing signals. Used to verify that the  correctly halts trading after the daily loss percentage floor is hit.

- **drawdown_circuit_breaker(symbol, price)** (New):
  Generates an extreme losing scenario designed to trigger the system-wide 15% drawdown circuit breaker, ensuring all execution is blocked until manual intervention.

## MacroScenarioBuilder

Located in , the  generates deterministic  objects for risk testing.

### Key Scenarios

- **nfp_shock**: High impact Non-Farm Payrolls event.
- **fomc_meeting**: Critical impact FOMC Rate Decision event.
- **geopolitical_crisis**: High impact geopolitical tension event.

## SystemContextBuilder

Located in , the  generates integrated test contexts combining price action, macro events, and risk status.

### Key Contexts

- **normal_trading**: Context for standard, low-risk trading.
- **high_impact_macro_event**: Context during a High-Impact news release (NFP), including a defensive .
- **extreme_volatility_with_risk_block**: Context with extreme price action (Flash Crash) and a defensive  (FOMC news block).

## RegimeTransitionScenarioBuilder

Located in , this builder generates sequences that transition between market states to test transition-score sensitivity.

### Key Methods

- **ranging_to_news_shock()**: Stable ranging followed by a sudden extreme news spike.
- **trending_to_reversal()**: Strong bullish trend followed by exhaustion and sharp reversal.
- **volatile_to_ranging()**: Extreme volatility phase that cools down into stable ranging.

## AdversarialScenarioBuilder

Located in , this builder creates "trap" scenarios to test technical robustness and noise rejection.

### Key Scenarios

- **wick_trap_cascade()**: Sequence of bars with small bodies but massive alternating wicks to test stop-loss sensitivity.
- **liquidity_void()**: Price jumps between bars without continuity (gaps) to test gap-detection logic.
- **vov_explosion()**: Ranging data where the volatility itself is extremely unstable to test VoV filters.
- **ema_crossover_flicker()**: Generates price action that oscillates rapidly around the EMA21 level, triggering frequent crossovers. Designed to test "signal flicker" and consistency guards.
- **rsi_boundary_oscillation()**: Pins RSI near critical thresholds (e.g., 70-75) to test boundary conditions and momentum filters.

## AnomalyScenarioBuilder

Located in `src/utils/synthetic_data.py`, this builder provides deterministic sequences for technical anomalies to test system robustness against data feed issues and noise.

### Key Scenarios

- **ghost_spikes()**: Generates extreme high/low wicks without impacting closing prices. This allows for testing of noise filters and ensuring the system isn't tricked by "bad" ticks.
- **stale_data_with_noise()**: Simulates a frozen data feed with minimal floating-point jitter to test "stale data" detection logic and handling of low-liquidity environments.

## InstitutionalFlowGenerator

Located in `src/utils/synthetic_data.py`, this generator provides deterministic price sequences simulating complex institutional market behavior and microstructure.

### Key Methods

- **stop_hunting(n_steps, start_price)**: Simulates a "stop hunt" where price moves steadily, dips sharply below a support level to trigger stops, and then reverses rapidly. Useful for testing stop-loss resilience and mean-reversion models.
- **iceberg_absorption(n_steps, start_price)**: Simulates price hitting a large hidden (iceberg) limit order. It results in a trend towards a level followed by multiple failed breakout attempts with high volume and minimal price progress. Useful for testing volume-weighted models and consolidation detection.
- **trend_exhaustion(n_steps, start_price)**: Simulates an exhausting trend consisting of a steady growth phase, a parabolic "blow-off top" (climax), and a sharp collapse. Essential for validating trend-following filters and exhaustion markers.

## Usage in Tests

These tools are designed to make tests deterministic and broad. See `tests/test_synthetic_data.py`, `tests/test_institutional_scenarios.py`, and `tests/test_enhanced_synthetic_scenarios.py` for implementation examples.

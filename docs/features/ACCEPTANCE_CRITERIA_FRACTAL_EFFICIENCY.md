# Acceptance Criteria: Institutional Fractal Efficiency & Regime Persistence

## Functional Acceptance Criteria
- **Behavior:**
    - Real-time calculation of the Hurst Exponent (H) and Fractal Dimension (D) for XAUUSD on multiple timeframes (M15, H1).
    - Classification of market efficiency into three states: Persistent (Trending), Anti-persistent (Mean Reverting), and Random Walk (Efficient).
    - Integration of fractal metrics into the `ExecutionFilter` to veto trend-following signals during efficient or anti-persistent regimes.
    - Detection of "Regime Decay" where fractal persistence drops below statistical significance thresholds.
- **Edge Cases:**
    - Handle insufficient historical data for R/S analysis or DFA by providing a "Neutral/Efficient" default.
    - Robustness against price gaps and outliers in high-frequency data.
    - Consistency across different lookback windows (e.g., 512 vs 1024 candles).
- **Inputs/Outputs:**
    - **Inputs:** High-fidelity OHLCV data (M15/H1).
    - **Outputs:** `FractalMetrics` (Hurst Exponent, Fractal Dimension, Persistence State).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for Hurst Exponent calculation using known persistent/random series (e.g., Brownian motion vs. Sine wave).
    - Integration tests verifying the `ExecutionFilter` correctly reacts to different fractal states.
- **Performance:**
    - Calculation of fractal metrics for a 1024-candle window must complete in < 100ms.
    - Asynchronous calculation to ensure no impact on the core trading loop latency.
- **Error Handling:**
    - Graceful fallback: If fractal calculation fails, the system must default to "Efficient" (H=0.5) and log a warning.
- **Observability:**
    - Log "Fractal Persistence State" transitions in the system audit log.
    - Display Hurst Exponent and state in the Decision Cockpit.

## Operational Acceptance
- **Documentation:**
    - Technical guide explaining Hurst Exponent interpretation and threshold selection.
    - README section on the Fractal Efficiency filter.
- **Configuration:**
    - `FRACTAL_LOOKBACK`: Number of candles for calculation.
    - `FRACTAL_TREND_THRESHOLD`: Hurst value required to confirm persistence (e.g., > 0.55).
- **Rollback:**
    - Feature flag to disable fractal filtering in the `ExecutionFilter`.
- **Monitoring:**
    - Alert if fractal metrics remain static or fail to update for > 4 hours.

## Release Readiness
- **Deployment:** Part of the "Advanced Differentiation" release tier.
- **Backward Compatibility:** No impact on existing technical or macro-based logic.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Quant Lead (Jules04).

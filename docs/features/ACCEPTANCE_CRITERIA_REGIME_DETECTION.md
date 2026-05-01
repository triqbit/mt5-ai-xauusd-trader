# Acceptance Criteria: Market Regime Detection

## Functional Acceptance Criteria
- **Behavior:** Classify XAUUSD market state into one of six predefined regimes (Trending, Ranging, Volatile Breakout, Low-Volatility Drift, News Shock, Mean Reversion) using statistical price features.
- **Edge Cases:**
    - Handle insufficient data for long-window calculations (graceful fallback or `None`).
    - Handle zero volatility (flat price) without division by zero errors.
    - Consistency between real-time `detect()` and historical `label_history()`.
- **Inputs/Outputs:**
    - **Inputs:** Pandas DataFrame containing OHLCV data.
    - **Outputs:** `RegimeInfo` object with `label` (string) and `confidence` (float 0.0-1.0).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each statistical feature calculation (ATR Ratio, Efficiency Ratio, Slope, Z-score).
    - Integration tests verifying regime transition logic on synthetic data.
- **Performance:**
    - Processing time for a single detection < 10ms.
    - Historical labeling for 10,000 candles < 500ms.
- **Error Handling:**
    - Validate input DataFrame columns (Close, High, Low required).
- **Observability:**
    - Log regime transitions at `INFO` level.
    - Expose current regime as a Prometheus/Monitoring metric.

## Operational Acceptance
- **Documentation:**
    - Reference: [Market Regime Detection](REGIME_DETECTION.md) (Technical Specs & Usage).
    - Description of statistical thresholds used for each regime.
- **Configuration:**
    - Configurable windows for short-term and long-term calculations via `config.yaml`.
- **Rollback:**
    - Ability to disable regime-aware logic in the ensemble model via feature flag.
- **Monitoring:**
    - Track regime distribution over time to detect market environment shifts.

## Release Readiness
- **Deployment:** Deployable as part of the `src.models` package.
- **Backward Compatibility:** Must not break `EnsembleModel` signature.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Lead Quant.

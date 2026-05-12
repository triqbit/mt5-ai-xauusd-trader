# Acceptance Criteria: Institutional Gold Flow & Physical Demand Proxies

## Functional Acceptance Criteria
- **Behavior:**
    - Automated daily ingestion of net flows for at least the top 2 Gold ETFs (GLD, IAU) from reliable sources (FRED/YFinance).
    - Real-time calculation of the Shanghai Gold Exchange (SGE) premium/discount relative to London Spot price.
    - Generation of a "Physical Support Score" (0-100) based on ETF flow momentum and SGE premiums.
    - Detection of "Physical-Paper Divergences" (e.g., price down while physical flows/premiums are up).
- **Edge Cases:**
    - Handle missing or delayed ETF AUM data by using the last known value with a "Stale" flag.
    - Filter out noise in SGE premiums caused by temporary currency fluctuations (USD/CNY).
    - Detect and alert on significant divergence events that may indicate a market bottom or top.
- **Inputs/Outputs:**
    - **Inputs:** Daily ETF AUM change, SGE Spot Price, London Spot Price, USD/CNY exchange rate.
    - **Outputs:** `PhysicalSupportScore`, `DivergenceSignal` (BULLISH_PHYSICAL, BEARISH_PHYSICAL, NEUTRAL), and detailed flow metrics.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the Physical Support Score calculation logic.
    - Mock tests for FRED/YFinance data ingestion.
    - Integration tests ensuring the score is correctly injected into the `EnsembleModel` feature vector.
- **Performance:**
    - Data harvesting and score calculation must complete in < 2 seconds during the daily refresh cycle.
    - Minimal impact on intraday trading loop (score is cached and updated daily/periodically).
- **Error Handling:**
    - Graceful degradation: If physical data is unavailable, the system should fall back to a "Neutral" physical score (50) and log a warning.
- **Observability:**
    - Log daily ETF flows and SGE premiums in the audit trail.
    - Display "Physical Demand: [Strong/Neutral/Weak]" and the Divergence Signal in the Decision Cockpit.

## Operational Acceptance
- **Documentation:**
    - Update `UNIQUE_FEATURES.md` with the technical implementation details of the Physical Demand Proxy.
    - Provide a runbook for troubleshooting data ingestion failures.
- **Configuration:**
    - `ETF_TICKERS`: List of ETFs to monitor.
    - `SGE_SYMBOL`: Symbol for Shanghai Gold Exchange data.
    - `PHYSICAL_DATA_REFRESH_CRON`: Frequency of data updates.
- **Rollback:**
    - Ability to disable the Physical Support Score in the ensemble via a feature flag.
- **Monitoring:**
    - Alert if the physical data feed remains stale for more than 48 hours.

## Release Readiness
- **Deployment:** Requires valid API keys for data providers (FRED/YFinance).
- **Backward Compatibility:** No impact on existing technical-only strategies.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Quant Research Lead (Jules04) and Product Steward (Jules05).

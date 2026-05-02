# Acceptance Criteria: XAUUSD Macro Sensitivity Overlays

## Functional Acceptance Criteria
- **Behavior:**
    - Integrate external data streams (FRED for Real Yields/DXY, YFinance for SPX/Commodities).
    - Calculate real-time correlations between XAUUSD and major macro drivers.
    - Provide a "Macro Risk Score" to the Pre-trade Intelligence Briefing.
- **Edge Cases:**
    - Handle missing data or API rate limits from FRED/YFinance.
    - Detect "Decoupling" events where historical correlations (e.g., Gold vs Real Yields) break down.
- **Inputs/Outputs:**
    - **Inputs:** External API keys (FRED), list of macro tickers.
    - **Outputs:** `MacroSensitivityMetrics` (correlations, volatility Z-scores, event risk).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for correlation calculation logic.
    - Mock tests for API data retrieval.
    - Integration test with the `PreTradeBriefing` aggregator.
- **Performance:**
    - Async data fetching to ensure macro updates don't block the trading loop.
    - Data caching (e.g., update macro factors every 1 hour) to reduce API calls.
- **Error Handling:**
    - Graceful fallback: If macro data is unavailable, the risk score should reflect higher uncertainty but not crash the system.
- **Observability:**
    - Log macro data fetch status and any "Correlation Breakdown" alerts.

## Operational Acceptance
- **Documentation:**
    - List of required API keys and how to configure them.
    - Guide on the "Macro-Defensive" trading mode.
- **Configuration:**
    - `FRED_API_KEY`: Secret.
    - `MACRO_UPDATE_INTERVAL`: How often to refresh macro data.
- **Rollback:**
    - Feature flag to disable macro overlays and return to pure technical trading.
- **Monitoring:**
    - Alert on "Stale Macro Data" if the last update was > 4 hours ago.

## Release Readiness
- **Deployment:** Requires valid API keys in the production environment.
- **Backward Compatibility:** No impact on systems not using macro filters.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Quant Lead (Jules04).

# Acceptance Criteria: Institutional Execution Analytics

## Functional Acceptance Criteria
- **Behavior:**
    - Calculate and track detailed execution metrics: Slippage (Pips/%), Fill Rate, Latency (Signal to Execution), and Market Impact.
    - Compare realized fill price against the requested bid/ask at signal time.
    - Provide an "Execution Quality Score" for each trade and broker account.
    - Integrate with the `PreTradeBriefing` to provide historical slippage forecasts.
- **Edge Cases:**
    - Handle "Requotes" and "Off-Quotes" errors from MT5.
    - Distinguish between "Normal" slippage and "Toxic" slippage (e.g., during news).
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal`, MT5 execution confirmation, Market Depth at entry.
    - **Outputs:** `ExecutionAnalytics` object linked to each `trade_id`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for slippage and latency calculations.
    - Integration test ensuring analytics are persisted for every trade.
- **Performance:**
    - Analytical processing must not add > 10ms to the post-trade closure cycle.
- **Error Handling:**
    - Graceful handling of missing market depth data.
- **Observability:**
    - Real-time "Slippage Heatmap" in the Decision Cockpit.
    - Prometheus gauges for average slippage and fill rates.

## Operational Acceptance
- **Documentation:**
    - Definition of all execution KPIs.
- **Configuration:**
    - `SLIPPAGE_ALERT_THRESHOLD`: Alert when slippage exceeds X pips.
- **Rollback:**
    - N/A.
- **Monitoring:**
    - Alert if fill rate drops below 95% over a 10-trade window.

## Release Readiness
- **Deployment:** Integrated with `src/analytics/execution_quality.py`.
- **Backward Compatibility:** N/A.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the Quant Research Lead (Jules04).

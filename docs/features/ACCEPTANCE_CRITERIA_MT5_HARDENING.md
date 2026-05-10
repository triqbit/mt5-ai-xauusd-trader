# Acceptance Criteria: MT5 Data Path Hardening

## Functional Acceptance Criteria
- **Behavior:**
    - Implement robust error handling and automatic recovery for all MT5 data requests (OHLCV, Tick, Account Info).
    - Use exponential backoff for reconnection attempts when the terminal connection is lost.
    - Gracefully handle "partial data" scenarios by validating bar counts and timestamps before processing.
    - Ensure that a failure in one data path (e.g., tick streaming) does not crash the entire trading loop.
- **Edge Cases:**
    - Handle `TERMINAL_NOT_FOUND`, `INTERNAL_ERROR_COMMUNICATION`, and `NOT_ENOUGH_RIGHTS` specifically.
    - Handle "Market Closed" states without triggering excessive reconnection attempts.
- **Inputs/Outputs:**
    - **Inputs:** Symbol, Timeframe, Number of bars.
    - **Outputs:** Validated `pd.DataFrame` or `None` with an error code; updated connection health metrics.

## Technical Acceptance
- **Test Coverage:**
    - 100% coverage of error handling paths using `unittest.mock`.
    - Simulated network latency and disconnection tests.
- **Performance:**
    - Zero memory growth in data polling loops over a 24-hour period.
    - Polling latency must not increase over time (stable P99 < 150ms).
- **Error Handling:**
    - All MT5 errors must be classified as `TRANSIENT` or `FATAL`.
    - Transient errors trigger retries; Fatal errors trigger the health gate / kill switch.
- **Observability:**
    - Log connection latencies and "Reconnection Events" with detailed error codes.
    - Real-time "Data Path Health" status displayed in the Decision Cockpit.

## Operational Acceptance
- **Documentation:**
    - Runbook for manual MT5 terminal recovery: `docs/runbooks/02-mt5-connection-outage.md`.
- **Configuration:**
    - `MT5_MAX_RETRIES`: Maximum number of reconnection attempts before escalating.
    - `MT5_RETRY_BACKOFF`: Base multiplier for exponential backoff.
- **Rollback:**
    - N/A (Internal robustness fix).
- **Monitoring:**
    - Alert on "MT5 Connection Persistent Failure" (> 5 minutes of outage during market hours).

## Release Readiness
- **Deployment:** Integral to the v1.1.0 release candidate.
- **Backward Compatibility:** Must maintain the same public interface for the `MT5Connector`.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Security & Quality Lead (Jules02).

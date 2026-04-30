# Acceptance Criteria: MT5 Cloud Connector (MetaAPI)

## Functional Acceptance Criteria
- **Behavior:** Provide a seamless connection to MetaTrader 5 via MetaAPI cloud services, allowing for non-Windows execution and high availability.
- **Edge Cases:**
    - Handle API rate limiting and connection timeouts.
    - Implement automatic failover between direct MT5 and MetaAPI if one is unavailable.
    - Sync state (positions/orders) correctly between the bot and the cloud.
- **Inputs/Outputs:**
    - **Inputs:** Symbol, timeframe, trade commands.
    - **Outputs:** OHLCV dataframes, order tickets, account status.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests using MetaAPI's sandbox or mock server.
    - Mock tests for all connector interface methods.
- **Performance:**
    - Data fetch latency < 200ms.
    - Order execution latency < 500ms.
- **Error Handling:**
    - Implement exponential backoff for reconnection.
    - Distinguish between transient network errors and permanent auth failures.
- **Observability:**
    - Log MetaAPI request/response metadata.
    - Expose metric for "Connection Latency" and "API Health Status".

## Operational Acceptance
- **Documentation:**
    - Setup guide for MetaAPI tokens and account IDs in `DEPLOYMENT_GUIDE.md`.
- **Configuration:**
    - Secret management for `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`.
- **Rollback:**
    - Ability to switch back to native MT5 connector via environment variable (`CONNECTOR_TYPE=native`).
- **Monitoring:**
    - Alert on "MetaAPI Unauthorized" or "Account Disconnected" events.

## Release Readiness
- **Deployment:** Requires MetaAPI account pre-provisioning.
- **Backward Compatibility:** Connector interface must remain identical to the native MT5 connector.
- **Migration:** No data migration; configuration updates only.
- **Sign-off:** Requires approval from the Infrastructure Lead.

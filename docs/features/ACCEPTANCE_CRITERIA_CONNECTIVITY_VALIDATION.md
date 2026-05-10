# Acceptance Criteria: MT5/MetaAPI Connectivity Validation

## Functional Acceptance Criteria
- **Behavior:**
    - Perform a "pre-flight" connectivity check during system startup to verify access to the MT5 terminal and/or MetaAPI cloud service.
    - Validate credentials (Account ID, Password, Token) and check for "Authorized" status.
    - Verify that the target trading symbols (e.g., XAUUSD) are visible and tradable on the current account.
    - Check the system time sync against the broker server time to prevent execution delays.
- **Edge Cases:**
    - Handle scenarios where the MT5 terminal is running but the account is logged out.
    - Detect "Investor Mode" (Read-only) and block the execution loop with a clear error.
- **Inputs/Outputs:**
    - **Inputs:** Configuration settings from `.env`.
    - **Outputs:** Startup log "Connectivity: [SUCCESS/FAIL]"; Exit code 1 on fail if `STRICT_STARTUP=True`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the validation logic with mocked MT5/MetaAPI responses.
    - Integration test verifying startup block on invalid credentials.
- **Performance:**
    - Total validation time must be < 2 seconds.
- **Error Handling:**
    - Provide actionable error messages (e.g., "Check METAAPI_TOKEN" vs "Broker Server Down").
- **Observability:**
    - Log detailed diagnostic info (MetaAPI latency, account balance, leverage) on success.

## Operational Acceptance
- **Documentation:**
    - Updated `SETUP_GUIDE.md` with a troubleshooting section for connectivity failures.
- **Configuration:**
    - `STRICT_STARTUP`: Boolean flag to determine if the bot should exit on connectivity failure.
- **Rollback:**
    - N/A (Safety gate).
- **Monitoring:**
    - Log connectivity status in the Audit Log as a "Startup Snapshot".

## Release Readiness
- **Deployment:** Mandatory for all production deployments.
- **Backward Compatibility:** No impact on existing connection logic; purely a pre-flight validation layer.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03).

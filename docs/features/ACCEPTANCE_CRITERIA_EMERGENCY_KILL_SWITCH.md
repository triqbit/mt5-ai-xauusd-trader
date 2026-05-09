# Acceptance Criteria: Emergency Kill Switch

## Functional Acceptance Criteria
- **Behavior:**
    - Immediately close all open positions for XAUUSD and other active symbols.
    - Cancel all pending orders (Limit/Stop).
    - Halt the core trading loop and prevent new signal execution.
    - Require manual intervention (explicit command or config change) to resume trading.
- **Edge Cases:**
    - Handle partial fills or failed order cancellations by retrying with exponential backoff.
    - Function correctly even if the database or other non-critical subsystems are down.
- **Inputs/Outputs:**
    - **Inputs:** `make emergency-stop` command or `KILL_SWITCH=True` environment variable.
    - **Outputs:** Confirmation of total flattening and "Halted" status in logs/audit trail.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the flattening logic using MT5 mocks.
    - Integration test ensuring the core loop stops when the kill switch is triggered.
- **Performance:**
    - Total time from trigger to last order cancellation must be < 2 seconds.
- **Error Handling:**
    - Log failures to close specific positions with high priority; retry logic must be robust.
- **Observability:**
    - Immediate high-priority alert to Telegram/Email.
    - Persistent "System Halted" state in the Audit Log and Redis.

## Operational Acceptance
- **Documentation:**
    - Standard Operating Procedure (SOP) for triggering the switch and recovering the system.
- **Configuration:**
    - `EMERGENCY_HALT_ON_FAILURE`: Boolean flag to trigger switch on critical health failure.
- **Rollback:**
    - N/A (Safety feature).
- **Monitoring:**
    - Dashboard indicator for "System Status" (Live/Halted).

## Release Readiness
- **Deployment:** Can be deployed independently.
- **Backward Compatibility:** No impact on existing trading logic.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03) and Security Lead (Jules02).

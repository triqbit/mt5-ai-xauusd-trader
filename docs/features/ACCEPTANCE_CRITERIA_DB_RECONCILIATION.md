# Acceptance Criteria: Database Operational State Reconciliation

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically synchronize the internal database state with the actual MetaTrader 5 terminal state upon system startup or reconnection.
    - Reconcile open positions: Ensure every position in MT5 is tracked in the database and vice-versa.
    - Reconcile pending orders: Verify all active limit/stop orders are correctly reflected in the system.
    - Update realized PnL and trade history for any trades closed while the bot was offline.
- **Edge Cases:**
    - Handle "Orphaned Positions" (found in MT5 but not in DB) by creating a "RECOVERED" trade entry.
    - Handle "Missing Positions" (found in DB but not in MT5) by marking them as "CLOSED_EXTERNALLY" with a best-guess exit price.
    - Robustness against MT5 terminal restarts or broker reconnections.
- **Inputs/Outputs:**
    - **Inputs:** MT5 current positions, MT5 trade history, local `trades` table.
    - **Outputs:** `ReconciliationReport` (Matched, Missing, Orphaned, Recovered) and a synchronized DB state.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests simulating database/MT5 divergence and verifying successful reconciliation.
    - Unit tests for the state matching logic (based on `ticket` or `magic_number`).
- **Performance:**
    - Reconciliation must complete in < 5 seconds during startup.
- **Error Handling:**
    - If reconciliation fails critically, the system must enter "SAFE_HALT" mode and prevent any new orders.
- **Observability:**
    - Log every reconciliation event with a summary of changes made to the database.

## Operational Acceptance
- **Documentation:**
    - Runbook for manual state reconciliation in case of catastrophic failure.
    - Explanation of the "RECOVERED" and "CLOSED_EXTERNALLY" trade statuses.
- **Configuration:**
    - `RECONCILE_ON_STARTUP` (bool).
    - `RECONCILE_INTERVAL`: Frequency of background checks (e.g., every 5 minutes).
- **Rollback:**
    - N/A (Consistency feature).
- **Monitoring:**
    - Alert if the reconciliation detects more than X% divergence between DB and MT5.

## Release Readiness
- **Deployment:** Foundational for system resilience.
- **Backward Compatibility:** Must support historical trade records.
- **Migration:** Schema update to include `reconciliation_status` if necessary.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).

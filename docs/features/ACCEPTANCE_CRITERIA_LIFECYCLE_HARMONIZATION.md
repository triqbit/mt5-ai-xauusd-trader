# Acceptance Criteria: Lifecycle Harmonization

## Functional Acceptance Criteria
- **Behavior:**
    - Implement a unified `main()` entry point that manages the initialization and execution of all system components.
    - Ensure a single, global instance of the `RiskManager` is shared across all modules to prevent conflicting risk decisions.
    - Implement a verified component shutdown sequence that ensures all resources (database connections, MT5 sessions, telemetry threads) are released cleanly.
- **Edge Cases:**
    - **Graceful Shutdown:** System must respond to SIGINT (Ctrl+C) and SIGTERM by completing the current poll cycle and executing the cleanup sequence.
    - **Re-initialization Guard:** Prevent re-initialization of already active components if the main loop is restarted internally.
    - **Initialization Failure:** If a critical component (MT5, Database) fails to initialize, the system must perform a partial cleanup of already-allocated resources and exit with a non-zero status code.
- **Inputs/Outputs:**
    - **Startup Output:** Structured logs showing unique initialization timestamps for each core component.
    - **Shutdown Output:** Confirmation logs for "Teardown Complete" across all initialized services.

## Technical Acceptance
- **Test Coverage:**
    - 100% test coverage for `LifecycleManager` state transitions (UNINITIALIZED -> INITIALIZING -> RUNNING -> SHUTTING_DOWN -> STOPPED).
    - Integration tests verifying that only one instance of `RiskManager` and `MT5Connector` exists in the process memory.
- **Performance:**
    - System initialization (from `main()` call to first market poll) must complete in < 2 seconds, excluding deep-learning model weight loading.
    - Zero redundant component instances (verified via memory profiling or object ID tracking in logs).
- **Error Handling:**
    - Any unhandled exception in the main loop must be caught, logged to the audit trail, and trigger a graceful shutdown attempt.
- **Observability:**
    - Startup telemetry (component version, health status) must be visible in the Decision Cockpit TUI.
    - Clear health check initialization logs using the `rich` library for scannability.

## Operational Acceptance
- **Documentation:**
    - Update `ARCHITECTURE_QUICK.md` to reflect the flattened, unified lifecycle and component hierarchy.
    - Provide a sequence diagram illustrating the startup and shutdown flow.
- **Configuration:**
    - All configuration validation (via `ConfigValidator`) must be successfully completed before any trading-critical component is initialized.
- **Rollback:**
    - Architectural changes must be modular enough to allow reverting to previous individual component initializations if regressions are detected in the unified loop.
- **Monitoring:**
    - Emit a "System Ready" event to the monitoring dashboard once the initialization sequence completes successfully.
    - Alert on "Abnormal Exit" if the process terminates without completing the shutdown sequence.

## Release Readiness
- **Deployment:** Verified against Release Candidate v1.1.0-rc7 and fully consolidated into the `main.py` execution loop.
- **Backward Compatibility:** All existing `BaseModel` and `BaseDataProvider` implementations must remain compatible with the new unified initialization sequence.
- **Migration:** No data migration required; architectural refactoring only.
- **Sign-off:** Requires approval from Jules05 (Integration Governor) and Jules03 (Release Reliability).

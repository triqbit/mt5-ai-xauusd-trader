# Acceptance Criteria: Demo Mode Safety & Account Validation

## Functional Acceptance Criteria
- **Behavior:**
    - Implement a "Safety Check Gate" in `MT5Connector` that queries the account type (DEMO vs REAL) via the MT5 API.
    - Force the system to exit with a critical error if the MT5 account type does not match the `TRADING_MODE` configuration (e.g., `TRADING_MODE=DEMO` but account is `REAL`).
    - Explicitly log the detected account number and type during the startup sequence.
    - Display a prominent "DEMO MODE ACTIVE" or "LIVE TRADING ACTIVE" warning in the Decision Cockpit TUI.
- **Edge Cases:**
    - Handle brokers that do not provide clear account type metadata by defaulting to a "Strict Mode" (manual override required).
    - Prevent accidental trades if the account type cannot be determined during initialization.
- **Inputs/Outputs:**
    - **Inputs:** `TRADING_MODE` environment variable, MT5 account metadata.
    - **Outputs:** Initialization Success or Critical Stop with detailed account/mode mismatch reason.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the account validation logic using mocked MT5 account info.
    - Integration tests verifying system shutdown on mode mismatch.
- **Performance:**
    - Account validation must be completed within < 500ms of MT5 terminal connection.
- **Error Handling:**
    - Mismatch errors must be classified as `FATAL` and prevent any order execution hooks from initializing.
- **Observability:**
    - High-priority audit log entry for every account validation event.
    - Visual indicator in the TUI (e.g., Red border for LIVE, Green for DEMO).

## Operational Acceptance
- **Documentation:**
    - Clearly document the safety gate behavior in `DEPLOYMENT_GUIDE.md`.
    - Provide instructions on how to explicitly authorize LIVE trading.
- **Configuration:**
    - `TRADING_MODE`: Must be either `DEMO` or `REAL`.
    - `FORCE_LIVE_CONFIRMATION`: Optional second flag for live execution.
- **Rollback:**
    - N/A (Safety feature).
- **Monitoring:**
    - Alert if the system is started in `REAL` mode on an account previously used for `DEMO` trading.

## Release Readiness
- **Deployment:** Mandatory for all production deployments.
- **Backward Compatibility:** N/A.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Security Lead (Jules02) and Risk Officer.

# Acceptance Criteria: Adaptive Capital-Preservation Operating Modes

## Functional Acceptance Criteria
- **Behavior:**
    - Switch the system between pre-defined risk postures: `DEFENSIVE`, `BALANCED`, `AGGRESSIVE`, `EVENT_PROTECTED`.
    - Adjust position sizes and risk limits dynamically based on the active mode.
    - Support manual overrides and automated switching (e.g., based on account drawdown).
- **Edge Cases:**
    - Ensure a transition between modes doesn't cause sudden liquidation of existing trades unless explicitly required by the new posture.
    - Handle invalid mode requests by defaulting to `DEFENSIVE`.
- **Inputs/Outputs:**
    - **Inputs:** `OperatingMode` enum, current account metrics.
    - **Outputs:** Adjusted risk parameters (Max Risk per Trade, Max Positions).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the `PostureManager` (state transitions).
    - Integration tests verifying `ExecutionFilter` and `RiskManager` respect the active posture.
- **Performance:**
    - Posture state lookup must be O(1) and ultra-fast (< 1ms).
- **Error Handling:**
    - Log all failed posture transitions.
- **Observability:**
    - Broadcast posture changes to Telegram and the Decision Cockpit.
    - Audit log entries for every mode switch (Who, When, Why).

## Operational Acceptance
- **Documentation:**
    - Detailed definition of each `OperatingMode` and its associated risk multipliers.
- **Configuration:**
    - Posture definitions should be hardcoded for safety but selectable via environment variables.
- **Rollback:**
    - Emergency "DEFENSIVE" mode activation via a single CLI command or TUI button.
- **Monitoring:**
    - Monitor "Mode Dwell Time" (how long the bot stays in each posture).

## Release Readiness
- **Deployment:** Part of the top-down risk governance framework.
- **Backward Compatibility:** Must default to `BALANCED` if no mode is specified.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).

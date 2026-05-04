# Acceptance Criteria: Institutional Decision Support System (DSS)

## Functional Acceptance Criteria
- **Behavior:**
    - Aggregate data from ML signals, market regime, macro risk, and performance metrics into a unified `DecisionPacket`.
    - Provide a "Go/No-Go" recommendation based on the combined status of all components.
    - Generate a high-fidelity terminal dashboard (TUI) for human-in-the-loop review in "Active Review" mode.
- **Edge Cases:**
    - Handle scenarios where one component (e.g., Macro Risk) is unavailable by flagging it as "Unknown" rather than blocking all trades.
    - Format terminal output correctly across various terminal sizes using the `rich` library.
    - Handle signals for multiple symbols simultaneously (if applicable).
- **Inputs/Outputs:**
    - **Inputs:** `SignalExplanation`, `RegimeInfo`, `RiskStatus`, and recent performance metrics (Sharpe, Win Rate, etc.).
    - **Outputs:** `DecisionPacket` (JSON/Pydantic) including `direction` and `consensus` fields, and a formatted string for terminal display.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for `DecisionPacket` validation and status aggregation logic.
    - Unit tests for `_calculate_consensus` logic covering Unanimous, Strong Majority, and Mixed states.
    - Integration tests for the `assemble_packet` method with mock component data.
    - Visual verification of the terminal output formatting (captured in logs or screenshots).
- **Performance:**
    - Packet assembly and formatting must take < 200ms to ensure low-latency decision support.
- **Error Handling:**
    - Graceful degradation if the `rich` library is not available (fallback to plain text).
- **Observability:**
    - Log the final `is_executable` status and blocking reasons for every decision packet generated.
    - Persist decision packets to the database for post-trade audit and "What-If" analysis.

## Operational Acceptance
- **Documentation:**
    - README section explaining how to read the DSS dashboard.
    - Technical documentation of the `DecisionPacket` schema for API integration.
- **Configuration:**
    - Feature flag to enable/disable the DSS layer in the trading loop.
    - Configurable "Strictness" levels (e.g., whether a "Yellow" macro risk blocks a trade).
- **Rollback:**
    - The DSS is an advisory/gate layer; it can be bypassed if it becomes a point of failure.
- **Monitoring:**
    - Dashboard panels should include system health status from the Enterprise Health Gate.

## Release Readiness
- **Deployment:** Requires the Explainability and Regime Detection modules to be active.
- **Backward Compatibility:** No impact on existing execution logic if disabled.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Product Steward (Jules05).

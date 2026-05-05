# Acceptance Criteria: Event Intelligence (Macro Guard)

## Functional Acceptance Criteria
- **Behavior:**
    - Ingest macroeconomic events from multiple providers (JSON, MetaAPI).
    - Normalize events into a standard `MacroEvent` schema with impact levels (Low to Critical).
    - Determine `RiskStatus` based on upcoming and ongoing events, applying pre-event blocks and post-event cooldowns.
    - Provide a `risk_multiplier` to adjust position sizes during high-volatility event windows.
- **Edge Cases:**
    - Handle provider connectivity failures by falling back to cached event data.
    - Handle long-duration events (multi-hour or multi-day) correctly.
    - Stricter blocking for major events (FOMC, NFP, Interest Rates) regardless of default impact score.
- **Inputs/Outputs:**
    - **Inputs:** Current timestamp, event window settings (pre/post minutes per impact).
    - **Outputs:** `RiskStatus` object (is_blocked, risk_multiplier, active_events, reason).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for `get_risk_status` using `MockEventProvider` with various event timings.
    - Integration tests with `MetaAPIEventProvider` (using mocked responses).
- **Performance:**
    - Risk status calculation must be fast (< 10ms) to avoid blocking the main trading loop.
- **Error Handling:**
    - Graceful fallback and logging when event fetching fails.
- **Observability:**
    - Log blocking events and risk multiplier changes at `INFO` level.
    - Expose `is_blocked` status to the real-time dashboard.

## Operational Acceptance
- **Documentation:**
    - List of supported event categories and their default risk windows.
- **Configuration:**
    - Configurable `pre_event_minutes` and `post_event_minutes` per impact level.
- **Rollback:**
    - Ability to disable macro blocking via a global `ENABLE_MACRO_GUARD=false` flag.
- **Monitoring:**
    - Alert if the event provider remains unreachable for more than 4 hours.

## Release Readiness
- **Deployment:** Critical safety component; must be deployed with updated cache management.
- **Backward Compatibility:** Must maintain compatibility with the `ExecutionFilter`.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).

# Acceptance Criteria: Decision Funnel Metrics

## Functional Acceptance Criteria
- **Behavior:**
    - Implement real-time tracking of trade signal "drops" as they pass through the decision funnel (Signal Generator -> Risk Manager -> Execution Filter -> Capital Allocator).
    - Every rejection event must be recorded as a Prometheus counter increment with standardized labels.
    - Labels must include: `component` (the module that rejected the signal) and `reason` (the specific rule that was violated).
- **Edge Cases:**
    - Ensure metrics are incremented correctly even during high-frequency signal bursts.
    - Handle scenarios where multiple filters within a single component (e.g., Execution Filter) would reject the signal; record the *primary* reason or use multi-labels if supported.
- **Inputs/Outputs:**
    - **Inputs:** Internal signal rejection events in `RiskManager`, `ExecutionFilter`, and `CapitalAllocator`.
    - **Outputs:** Prometheus counter `trading_internal_rejections_total`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each rejection point (Circuit Breaker, Confidence Threshold, Drawdown Limit, etc.) verifying that the counter is incremented with the correct labels.
    - Integration test with the `Monitor` class to verify endpoint accessibility.
- **Performance:**
    - Metric increment latency < 0.1ms (non-blocking).
- **Error Handling:**
    - Failures in the Prometheus client must not impact the core trading logic.
- **Observability:**
    - Metrics must be viewable via the `/metrics` endpoint in Prometheus format.

## Operational Acceptance
- **Documentation:**
    - A "Rejection Reason Dictionary" documenting every possible `reason` label and its meaning.
    - Grafana dashboard template (JSON) visualizing the Decision Funnel (funnel chart showing signal drop-offs).
- **Configuration:**
    - Feature flag to toggle detailed rejection tracking (`METRICS_DECISION_FUNNEL_ENABLED`).
- **Rollback:**
    - N/A (Observability).
- **Monitoring:**
    - Alert if a specific component's rejection rate exceeds 50% over a 5-minute window (detecting misconfiguration).

## Release Readiness
- **Deployment:** Part of the "Enterprise Observability" release tier.
- **Backward Compatibility:** No impact on existing trading logic or signals.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Observability & Quality Lead (Jules02) and Product Steward (Jules05).

# Acceptance Criteria: Structured Iteration Heartbeat

## Functional Acceptance Criteria
- **Behavior:**
    - Emit a high-fidelity "heartbeat" signal at the beginning and end of every trading loop iteration.
    - Record the wall-clock duration of each complete iteration.
    - Attribute any loop failures or timeouts to specific sub-modules (e.g., Data Ingestion, Model Inference, Risk Validation).
    - Calculate a "Market Stability" metric based on the variance of loop processing times relative to market volatility.
- **Edge Cases:**
    - Handle sub-millisecond iterations without loss of precision using monotonic clocks.
    - Detect and log "Stuck" iterations where a component blocks for longer than the defined timeout.
- **Inputs/Outputs:**
    - **Inputs:** Trading loop state and execution context.
    - **Outputs:** Prometheus gauges (`trading_iteration_heartbeat_timestamp`, `trading_iteration_duration_seconds`) and "Slow Loop" warnings in the audit log.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the `Heartbeat` utility to verify timing accuracy.
    - Integration tests in `main.py` ensuring metrics are updated even if a trading signal is not generated.
- **Performance:**
    - Heartbeat recording overhead must be < 0.1ms per iteration.
- **Error Handling:**
    - Any failure in the heartbeat or telemetry logic must be caught and logged, and must never block or crash the primary trading loop.
- **Observability:**
    - Integration with the Decision Cockpit TUI to show real-time "Loop Latency" and "Last Active" status.

## Operational Acceptance
- **Documentation:**
    - Runbook entry for diagnosing "Late Heartbeat" alerts.
- **Configuration:**
    - `HEARTBEAT_LOG_INTERVAL`: Interval for emitting heartbeat status to the text log (default: 60s).
    - `MAX_ITERATION_LATENCY`: Threshold (in seconds) before a "Critical Latency" alert is triggered.
- **Rollback:**
    - Feature flag to disable detailed heartbeat telemetry if resource usage becomes a concern.
- **Monitoring:**
    - Prometheus alert rule: `time() - trading_iteration_heartbeat_timestamp > 10` (if loop is expected every 5s).

## Release Readiness
- **Deployment:** Core system improvement; deployed as part of the trading engine.
- **Backward Compatibility:** No impact on existing trading logic or model interfaces.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Core Development Lead (Jules01) and Product Steward (Jules05).

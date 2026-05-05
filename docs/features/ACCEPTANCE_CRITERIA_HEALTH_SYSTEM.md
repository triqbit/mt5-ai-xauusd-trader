# Acceptance Criteria: Enterprise Health System (Monitoring & Gating)

## Functional Acceptance Criteria
- **Behavior:**
    - Monitor the health of all critical system components: MT5, Database, Models, Config, Disk, Redis, Audit Log.
    - Provide a unified `HealthReport` with statuses: `HEALTHY`, `DEGRADED`, `FAILED`.
    - Enforce a `startup_gate` that blocks execution if any critical component is `FAILED`.
    - Expose health metrics via a REST API (FastAPI) and Prometheus `/metrics` endpoint.
- **Edge Cases:**
    - Active connectivity checks for MT5 (account info fetch) to detect "zombie" connections.
    - Disk space monitoring for log directories.
    - Non-blocking checks for optional components (e.g., Redis should only cause `DEGRADED`).
- **Inputs/Outputs:**
    - **Inputs:** Component instances (Connector, Logger, Model, etc.).
    - **Outputs:** `HealthReport` Pydantic model.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each individual health check (MT5, DB, Config, etc.) using mocks.
    - Integration test for the `startup_gate` and FastAPI endpoints.
- **Performance:**
    - A full health report generation must take < 2 seconds (constrained by network timeouts).
- **Error Handling:**
    - The `HealthChecker` itself must be exception-proof; internal failures should return a `FAILED` status for the checker itself.
- **Observability:**
    - Export health statuses to Prometheus Gauges.
    - Log "Startup Health Gate" results to the Audit Log.

## Operational Acceptance
- **Documentation:**
    - API documentation for `/health/liveness`, `/health/readiness`, and `/health/full`.
- **Configuration:**
    - Configurable disk space thresholds.
- **Rollback:**
    - N/A.
- **Monitoring:**
    - Dashboard visualization of component health over time.

## Release Readiness
- **Deployment:** Integrated with Docker healthchecks and Kubernetes probes (if used).
- **Backward Compatibility:** N/A.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03).

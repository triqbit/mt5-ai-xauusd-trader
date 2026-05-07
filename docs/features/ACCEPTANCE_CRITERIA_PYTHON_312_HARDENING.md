# Acceptance Criteria: Python 3.12 Compatibility Hardening

## Functional Acceptance Criteria
- **Behavior:**
    - The system must run without errors or deprecation warnings on Python 3.12.
    - All `datetime.utcnow()` and `datetime.utcfromtimestamp()` calls must be replaced with timezone-aware `datetime.now(UTC)` or `datetime.fromtimestamp(ts, UTC)`.
    - Ensure all dependencies are compatible with Python 3.12, specifically `pandas`, `numpy`, and `pandas-ta`.
- **Edge Cases:**
    - Correct handling of timezone transitions in historical data processing.
    - Graceful handling of any removed modules in Python 3.12 (e.g., `distutils`).
- **Inputs/Outputs:**
    - **Inputs:** Current codebase, requirements files.
    - **Outputs:** Zero deprecation warnings in logs, successful execution of all test suites on Python 3.12.

## Technical Acceptance
- **Test Coverage:**
    - Verify that all time-sensitive tests (risk management, signal generation) pass with the new `datetime` patterns.
    - CI pipeline must include a job specifically running on Python 3.12.
- **Performance:**
    - No regression in startup time or inference latency on Python 3.12 compared to 3.11.
- **Error Handling:**
    - Catch and report any `AttributeError` or `ImportError` related to Python 3.12 breaking changes.
- **Observability:**
    - Log the Python runtime version on startup.

## Operational Acceptance
- **Documentation:**
    - Update `SETUP_GUIDE.md` and `README.md` to specify Python 3.12+ as the recommended version.
- **Configuration:**
    - Update `Dockerfile` to use `python:3.12-slim`.
- **Rollback:**
    - Maintain backward compatibility with Python 3.11 until the 3.12 migration is fully validated in production.
- **Monitoring:**
    - Alert on any "Unhandled Exception" clusters that coincide with the 3.12 rollout.

## Release Readiness
- **Deployment:** Integral to the v1.1.0 release.
- **Backward Compatibility:** Must remain compatible with Python 3.11 for a minimum of one release cycle.
- **Migration:** Users must be instructed to update their local environments to 3.12.
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Security & Quality Lead (Jules02).

# Acceptance Criteria: Environment Stability & Reproducibility

## Functional Acceptance Criteria
- **Behavior:**
    - Ensure that the system can be built and run consistently across different platforms (Linux, Windows, macOS/ARM) using standardized dependency files.
    - Implement a clear hierarchy of requirement files:
        - `requirements.txt`: Core runtime dependencies (highly pinned).
        - `requirements-dev.txt`: Development and testing tools.
        - `requirements-ci.txt`: CI-specific pins to ensure pipeline stability.
    - Docker builds must be reproducible (using specific base image hashes and multi-stage builds).
- **Edge Cases:**
    - Handle platform-specific dependency clashes (e.g., `metaapi-cloud-sdk` vs. `python-socketio` version requirements).
    - Support for environments without specific hardware (e.g., no GPU for ML models) via optional dependency groups or graceful fallbacks.
- **Inputs/Outputs:**
    - **Inputs:** Dependency lock files and platform-specific requirement overrides.
    - **Outputs:** A consistent `pip list` output across identical environments; successful Docker image build.

## Technical Acceptance
- **Test Coverage:**
    - Automated "Dependency Consistency" check in CI to verify that all requirement files are synchronized.
    - Multi-platform smoke tests (Linux/Docker) verifying that the app starts up without import errors.
- **Performance:**
    - Docker build time < 5 minutes (using layers and caching).
    - Virtual environment creation time < 2 minutes.
- **Error Handling:**
    - Clear errors if a dependency cannot be resolved or if there is a version conflict (using `pip-check` or similar).
- **Observability:**
    - Log the exact versions of all major libraries (PyTorch, Pandas, MT5) during startup for auditability.

## Operational Acceptance
- **Documentation:**
    - "Environment Management Guide" in the docs explaining how to update dependencies safely.
    - README section on Docker deployment and configuration.
- **Configuration:**
    - Support for `.env`-based environment selection (e.g., `ENV=prod`, `ENV=dev`).
- **Rollback:**
    - Ability to revert to a previous "Dependency Snapshot" via Git.
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Critical for ensuring that "it works on my machine" translates to "it works in production."
- **Backward Compatibility:** Must support the existing Python 3.12 target.
- **Migration:** Retroactive stabilization of any divergent requirement files.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03) and Core Development Lead (Jules01).

# Acceptance Criteria: Enterprise Python Standards & Linting

## Functional Acceptance Criteria
- **Behavior:**
    - Enforce a unified coding style across the entire repository using `Ruff`.
    - Enforce type hinting for all function signatures using `MyPy` (Strict mode for core/trading).
    - Prevent the use of unsafe or deprecated Python functions (e.g., `datetime.utcnow()`).
    - Standardize docstring format (Google/NumPy style).
- **Edge Cases:**
    - Support for third-party libraries without type stubs (using `# type: ignore`).
    - Allow for exclusions in legacy or research-only modules.
- **Inputs/Outputs:**
    - **Inputs:** Python source code.
    - **Outputs:** Linting reports, Type-check status, Formatted code.

## Technical Acceptance
- **Test Coverage:**
    - Mandatory CI check: PRs cannot be merged if `Ruff` or `MyPy` fails.
- **Performance:**
    - Linting and type-checking must complete in < 2 minutes.
- **Error Handling:**
    - Direct links to the line of code causing the violation in the CI output.
- **Observability:**
    - Repository health badge for "Linting" and "Types".

## Operational Acceptance
- **Documentation:**
    - Coding Standards Guide (`AGENTS.md` or `CONTRIBUTING.md`).
- **Configuration:**
    - Centralized `pyproject.toml` configuration for all tools.
- **Rollback:**
    - Automated code formatting (`ruff format`) on commit.
- **Monitoring:**
    - Track "Technical Debt" (total number of linting/type warnings).

## Release Readiness
- **Deployment:** Strictly internal developer tooling.
- **Backward Compatibility:** N/A.
- **Migration:** Retroactive formatting of all existing source code.
- **Sign-off:** Requires approval from the Core Development Lead (Jules01).

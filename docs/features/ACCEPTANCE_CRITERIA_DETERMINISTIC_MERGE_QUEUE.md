# Acceptance Criteria: Deterministic Merge Queue

## Functional Acceptance Criteria
- **Behavior:**
    - PRs must be processed and ordered deterministically based on risk classification (High, Medium, Low) and submission timestamp.
    - Automated rebase onto `main` is required for all PRs to maintain a strictly linear history.
    - Integration gates: All CI checks (linting, tests, >80% coverage) must pass before a PR is eligible for the "Merge Ready" state.
    - Risk-based gating: High-risk PRs (touching risk, trading, or core) require explicit escalation and potentially manual sign-off despite passing CI.
- **Edge Cases:**
    - Detect and block "Disconnected Root" PRs that do not share a common ancestor with the current `main` branch.
    - Automatically flag PRs with merge conflicts or stale dependencies for manual remediation.
    - Handle GitHub API rate limits by implementing an exponential backoff strategy in the triage generator.
- **Inputs/Outputs:**
    - **Inputs:** Open Pull Requests, GitHub Actions CI status, Risk Mapping (file paths).
    - **Outputs:** Updated `PR_TRIAGE_DAILY.md` dashboard and automated `merge` or `rebase` operations.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the risk classification logic and file-path heuristics.
    - Integration tests verifying the triage sorting and dashboard generation logic.
- **Performance:**
    - Full triage processing and report generation for up to 1,000 open PRs must complete in < 5 minutes.
- **Error Handling:**
    - Fail "Safe": If the triage script cannot reach the GitHub API, it must not perform any automated merges and should log a high-priority warning.
- **Observability:**
    - Maintain a daily `PR_TRIAGE_DAILY.md` audit log of all triage decisions and risk classifications.

## Operational Acceptance
- **Documentation:**
    - Authoritative guide in `docs/integration/merge_queue.md` explaining the deterministic sorting and rebase logic.
- **Configuration:**
    - `AUTO_MERGE_POLICY.md` must define the current strictness levels and blocking patterns.
- **Rollback:**
    - Ability to globally disable the automated merge queue via a repository environment variable or feature flag.
- **Monitoring:**
    - Track and report the "Mean Time to Merge" and "Rebase Failure Frequency" in the project health dashboard.

## Release Readiness
- **Deployment:** Foundational governance infrastructure; independent of trading loop.
- **Backward Compatibility:** Must support all existing feature and jules* branch naming conventions.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Product Steward (Jules05).

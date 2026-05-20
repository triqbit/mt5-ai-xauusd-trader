# Acceptance Criteria: Strict Auto-Merge Policy

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically enable auto-merge for Pull Requests that satisfy all safety gates: 100% CI pass, Code Coverage >= 80%, clean security scans, and Code Owner approval.
    - Explicitly block and label as `escalated-risk` any Pull Request that modifies high-risk domains: `src/trading/`, `src/core/risk_engine.py`, `src/core/config.py`, `.env` files, Docker configurations, or CI/CD deployment workflows.
    - Ensure that PRs touching `src/` or `main.py` include mandatory updates to documentation and tests.
- **Edge Cases:**
    - Detect "piggybacking" where low-risk changes are bundled with high-risk modifications in a single PR.
    - Handle PRs from "Disconnected Root" branches by blocking merge and requesting a rebase.
    - Manage GitHub API rate limits during high-volume PR triage.
- **Inputs/Outputs:**
    - **Inputs:** PR file list, CI status codes, Coverage percentage, Label status, Approver list.
    - **Outputs:** Automated merge execution, `escalated-risk` label application, or descriptive blocking comment.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the file-pattern matching logic (regex-based path filtering).
    - Integration tests verifying the triage decision tree against a suite of synthetic PR payloads.
- **Performance:**
    - Triage decision and labeling must complete in < 60 seconds from the `pull_request` event.
- **Error Handling:**
    - **Fail-Safe:** If the policy engine cannot verify all conditions (e.g., GitHub API timeout), it must default to a "Block" state.
- **Observability:**
    - Maintain a persistent audit log of all auto-merge decisions in `docs/integration/AUTO_MERGE_POLICY.md`.
    - Log the specific policy rule that triggered a block or escalation.

## Operational Acceptance
- **Documentation:**
    - Authoritative policy definition maintained in `docs/integration/AUTO_MERGE_POLICY.md`.
    - Runbook for manual override of the auto-merge gate for emergency fixes.
- **Configuration:**
    - High-risk file patterns must be defined in `.github/workflows/auto-merge-policy.yml` and synchronized with the documentation.
- **Rollback:**
    - Ability to disable auto-merge functionality globally via a repository environment variable.
- **Monitoring:**
    - Alert if a PR is merged into `main` without satisfying the policy (detected via post-merge audit).

## Release Readiness
- **Deployment:** Independent governance infrastructure; no impact on trading loop latency.
- **Backward Compatibility:** N/A.
- **Migration:** Retroactive audit of existing open PRs against the new strict policy.
- **Sign-off:** Requires approval from the Product Steward (Jules05) and Release Reliability Lead (Jules03).

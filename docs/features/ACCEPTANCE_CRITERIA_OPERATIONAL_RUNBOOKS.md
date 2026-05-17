# Acceptance Criteria: Operational Runbooks

## Functional Acceptance Criteria
- **Behavior:**
    - Provide standardized, actionable procedures for system maintenance, emergency response, and recovery.
    - Each runbook must follow a consistent template: Purpose, Prerequisites, Step-by-Step Procedure, Verification, and Rollback.
    - Coverage must include: MT5 Reconnection, Database Restoration, Emergency Kill Switch recovery, and Configuration Hot-swapping.
- **Edge Cases:**
    - Procedures for "Blind Recovery" where the primary dashboard or logging system is unavailable.
    - Instructions for manual trade reconciliation during extreme broker downtime.
- **Inputs/Outputs:**
    - **Inputs:** Operational incident or maintenance window.
    - **Outputs:** Resolved incident, verified system state, and updated audit trail.

## Technical Acceptance
- **Test Coverage:**
    - "Fire Drill" verification: Every runbook must be successfully executed and verified in the `pre-prod` or `demo` environment before being marked as `PROD_READY`.
    - Verification of shell commands and SQL scripts included in the runbooks.
- **Performance:**
    - Critical procedures (e.g., Emergency Stop) must have estimated "Time to Completion" recorded.
- **Error Handling:**
    - Every major step must include "Troubleshooting" or "Common Failure Points" section.
- **Observability:**
    - Record the execution of an operational runbook in the system audit log.

## Operational Acceptance
- **Documentation:**
    - Standardized naming convention: `docs/operations/RUNBOOK_[category]_[action].md`.
    - Runbooks must be accessible in plain text (Markdown) for offline use.
- **Configuration:**
    - N/A.
- **Rollback:**
    - Every procedure must include an explicit "Rollback" or "Back-out" plan.
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Mandatory requirement for v1.1.0 and future production releases.
- **Backward Compatibility:** Runbooks must explicitly state the system versions they support.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Release Reliability Lead (Jules03).

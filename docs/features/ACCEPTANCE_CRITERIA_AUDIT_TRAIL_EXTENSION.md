# Acceptance Criteria: Audit Trail Extension (Compliance & Forensics)

## Functional Acceptance Criteria
- **Behavior:**
    - Extend the `AuditLogger` to capture full "Decision Context" for every trade, including raw model scores, active risk filters, and the current market regime snapshot.
    - Capture "Negative Audit" events: Explicitly log why a signal was REJECTED by the `ExecutionFilter` or `RiskManager`.
    - Implement an "Immutable Checksum" for every audit log entry to prevent tampering or accidental deletion.
    - Export audit logs in an "Auditor-Ready" format (CSV or Signed PDF).
- **Edge Cases:**
    - Handle high-frequency "Audit Bursts" without blocking the trading loop.
    - Ensure audit logs are preserved even during severe system crashes or disk failures (implement "Audit Sync" to remote storage).
- **Inputs/Outputs:**
    - **Inputs:** State snapshots from all decision-making modules.
    - **Outputs:** Enhanced `audit_logs` database records, periodic "Compliance Reports".

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the "Negative Audit" logging path.
    - Integration tests verifying that every trade signal (approved or rejected) results in an audit entry.
    - Verification of log checksum integrity.
- **Performance:**
    - Audit logging latency < 5ms (asynchronous/non-blocking).
- **Error Handling:**
    - If the audit log cannot be written (e.g., disk full), the bot must enter a "SAFE_HALT" mode.
- **Observability:**
    - "Audit Integrity Check" task to periodically verify that log history matches checksums.

## Operational Acceptance
- **Documentation:**
    - Description of the "Decision Context" schema for auditors.
    - Guide for law/compliance teams on how to query and export the audit trail.
- **Configuration:**
    - `AUDIT_LOG_LEVEL`: e.g., "ESSENTIAL", "FULL_TRACE".
    - `AUDIT_REMOTE_SYNC_ENABLED`: (bool).
- **Rollback:**
    - N/A (Compliance improvement).
- **Monitoring:**
    - Alert on "Audit Checksum Mismatch" or "Audit Sync Failure".

## Release Readiness
- **Deployment:** Managed via `src/core/audit_log.py` updates.
- **Backward Compatibility:** Must support viewing/parsing of legacy audit log entries.
- **Migration:** Schema update for the `audit_log` table to include `decision_metadata` (JSONB) and `checksum`.
- **Sign-off:** Requires approval from the Compliance Officer and Security & Quality Lead (Jules02).

# Acceptance Criteria: Enterprise Secret Rotation

## Functional Acceptance Criteria
- **Behavior:**
    - Support rotation of MT5 credentials, Database passwords, and API keys (FRED, Telegram).
    - Allow for seamless transition without manual restarts if the secrets provider supports it.
    - Validate new secrets before applying them to the live environment.
- **Edge Cases:**
    - Handle rotation failures by reverting to the previous known-good secret (if supported by provider).
    - Manage "Dual-Active" periods where both old and new secrets are temporarily valid.
- **Inputs/Outputs:**
    - **Inputs:** Signal from secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).
    - **Outputs:** Updated internal configuration and successful re-authentication logs.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the configuration reloading logic.
    - Integration test with a mock secrets provider.
- **Performance:**
    - Secret rotation must not cause a trading loop latency spike > 500ms.
- **Error Handling:**
    - Critical alert if rotation fails or if the new secret is invalid.
- **Observability:**
    - Log rotation events (masked) in the Audit Log.

## Operational Acceptance
- **Documentation:**
    - Guide on configuring external secrets managers.
    - Runbook for manual secret recovery.
- **Configuration:**
    - `SECRETS_PROVIDER`: Type of secrets manager.
    - `ROTATION_GRACE_PERIOD`: Time to keep old secrets valid.
- **Rollback:**
    - Automated rollback to cached "Last Known Good" configuration.
- **Monitoring:**
    - Monitor "Secret Age" and alert if rotation hasn't occurred within the policy window.

## Release Readiness
- **Deployment:** Requires infrastructure setup (Secret Manager).
- **Backward Compatibility:** Must support legacy `.env` file loading.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Security Lead (Jules02).

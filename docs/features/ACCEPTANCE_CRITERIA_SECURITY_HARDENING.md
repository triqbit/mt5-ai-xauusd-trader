# Acceptance Criteria: System Security Hardening

## Functional Acceptance Criteria
- **Behavior:**
    - Enforce restrictive filesystem permissions (`0o700`) on all operational directories (`data/`, `logs/`, `models/trained/`).
    - Enforce restrictive permissions (`0o600`) on the `.env` file containing secrets.
    - Enable `PRAGMA secure_delete=ON` for all SQLite databases to overwrite deleted data with zeroes.
    - Mask all fields in `TradingConfig` annotated with `SecretStr` in every log output, regardless of log level or destination.
- **Edge Cases:**
    - Handle existing files with permissive permissions by automatically correcting them during system initialization.
    - Ensure `secure_delete` does not significantly degrade performance during high-frequency trade logging.
- **Inputs/Outputs:**
    - **Inputs:** Operational file paths and configuration objects.
    - **Outputs:** Secure file attributes, zeroed-out deleted database pages, and sanitized log strings.

## Technical Acceptance
- **Test Coverage:**
    - Automated tests verifying directory and file permissions (`stat.S_IRWXU` checks).
    - Unit tests for the `SecretMaskingProcessor` verifying no leaks for various secret lengths.
    - Verification that `PRAGMA secure_delete` is active on the database connection.
- **Performance:**
    - Permission enforcement overhead should be negligible (< 100ms) and only occur at startup.
    - `secure_delete` overhead < 5ms per transaction.
- **Error Handling:**
    - If permissions cannot be enforced (e.g., on a filesystem that doesn't support them), the system must emit a CRITICAL warning but may proceed if `STRICT_SECURITY=False`.
- **Observability:**
    - Log a "Security Hardening Complete" event at startup with a summary of enforced measures.

## Operational Acceptance
- **Documentation:**
    - Update `SECURITY.md` with the new hardening measures and directory structure requirements.
- **Configuration:**
    - `STRICT_SECURITY`: Boolean flag (default `True`) to determine if startup should fail on security validation errors.
- **Rollback:**
    - N/A (Security requirement).
- **Monitoring:**
    - Periodic security audit task to verify permissions have not drifted.

## Release Readiness
- **Deployment:** Core security improvement; mandatory for all environments.
- **Backward Compatibility:** No impact on existing trading or model logic.
- **Migration:** Automatically applies to existing data and log directories on first run.
- **Sign-off:** Requires approval from the Security Lead (Jules02) and Lead Developer (Jules01).

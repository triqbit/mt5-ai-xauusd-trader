# Acceptance Criteria: Log Sanitization & Secret Masking

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically detect and redact sensitive credentials from all system logs, including MetaTrader 5 passwords, database credentials, API tokens (MetaAPI, Telegram), and account balances.
    - Implement a `SecretMaskingProcessor` in the `structlog` pipeline that replaces identified secrets with `[MASKED]`.
    - Support dynamic secret discovery by inspecting the `TradingConfig` for fields annotated with `pydantic.SecretStr`.
- **Edge Cases:**
    - Correctly parse and mask passwords embedded in connection strings (e.g., `DATABASE_URL`).
    - Handle multi-line log messages or nested dictionary structures without leaking secrets.
    - Ensure that masking does not redact non-sensitive substrings that happen to match part of a secret (e.g., if a password is "pass123", do not mask the word "password").
- **Inputs/Outputs:**
    - **Inputs:** Raw log events (key-value pairs) containing potential secrets.
    - **Outputs:** Sanitized log events where all sensitive values are replaced with `[MASKED]`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the masking regex and pattern matching logic.
    - Integration tests verifying that secrets defined in `.env` are never printed to `stdout` in any log level (DEBUG/INFO/ERROR).
- **Performance:**
    - Masking processor overhead must be < 0.5ms per log event to maintain high-frequency trading performance.
- **Error Handling:**
    - If the masking processor fails, it must fail "safe" by either blocking the log entry or masking the entire message.
- **Observability:**
    - Log an internal warning (without secrets) if a masking collision or error is detected.

## Operational Acceptance
- **Documentation:**
    - Technical overview of the sanitization architecture in `docs/operations/LOG_SANITIZATION.md`.
    - Coding guidelines for defining new secrets using `SecretStr`.
- **Configuration:**
    - Enabled by default in all operating modes.
    - Allow for a configurable list of additional "sensitive keys" to be masked.
- **Rollback:**
    - N/A (Security requirement).
- **Monitoring:**
    - Periodic audit of log artifacts to verify zero leakage of plaintext secrets.

## Release Readiness
- **Deployment:** Integral part of the `src/core/log_config.py` module.
- **Backward Compatibility:** Must support redaction of legacy log formats during the transition to `structlog`.
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Security Lead (Jules02) and Lead Developer (Jules01).

# Acceptance Criteria: Config Validation (Startup Guard)

## Functional Acceptance Criteria
- **Behavior:**
    - Perform a comprehensive audit of all environment variables and configuration settings at startup.
    - Enforce mandatory fields (MT5 credentials, secrets) and validate their format.
    - Verify existence of critical local files (model paths, MT5 terminal path on Windows).
    - Enforce "Risk Parity" by validating risk parameters against enterprise safety bounds.
    - Block startup if any "Critical" validation errors are found.
- **Edge Cases:**
    - Detect and block default placeholder secrets (e.g., "CHANGE_ME", "YOUR_TOKEN").
    - Enforce explicit user confirmation (`CONFIRM_LIVE_TRADING=YES`) for live mode.
    - Validate cross-component consistency (e.g., if Telegram token is provided, chat ID must also be present).
- **Inputs/Outputs:**
    - **Inputs:** `TradingConfig` instance.
    - **Outputs:** `ValidationResult` containing a success boolean and a list of `ValidationError` objects (field, message, severity, remedy).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests covering every validation rule in `src/core/config_validator.py`.
    - Integration test ensuring `startup_gate` in `HealthChecker` triggers on validation failure.
- **Performance:**
    - Validation suite must complete in < 100ms.
- **Error Handling:**
    - Validation logic itself must be robust and not raise exceptions.
- **Observability:**
    - Log every validation failure with its associated remedy.
    - Log "Startup Health Gate PASSED/FAILED" to the Audit Log.

## Operational Acceptance
- **Documentation:**
    - Detailed `RISK_LIMITS.md` (or similar) mapping configuration bounds to policy.
- **Configuration:**
    - Validation rules must align with `TradingConfig` defaults and environment overrides.
- **Rollback:**
    - Validation can be bypassed for non-critical warnings but NOT for critical errors.
- **Monitoring:**
    - Failed startup attempts due to config errors should be captured in the deployment log.

## Release Readiness
- **Deployment:** Integral to the startup sequence; deployed with the core bot.
- **Backward Compatibility:** Must support all legacy configuration keys until officially deprecated.
- **Migration:** No data migration; requires updating `.env` files if new mandatory fields are added.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).

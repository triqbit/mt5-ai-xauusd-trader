# Security Hardening: Secure Model Loading and Auto-Permission Hardening

## Overview
This document details the security hardening measures implemented to protect against unsafe deserialization and insecure file permissions.

## 1. Secure Model Loading
The `RegimeDetector` has been hardened to prevent arbitrary code execution via malicious model files.

### Path Validation
- **Requirement:** Model files must be located within the project's `models/` directory or system-standard temporary directories (`/tmp`, `/var/tmp`).
- **Implementation:** Uses `pathlib.Path.is_relative_to` for robust path validation, preventing bypass attempts such as sibling directory attacks (e.g., `/app/models_attacker/`).
- **Fail-Closed Design:** If the project root cannot be determined or path safety cannot be verified, the system will refuse to load the model.

### Permission Checks
- **Requirement:** Model files must have restrictive permissions to prevent unauthorized tampering.
- **Implementation:** On Linux/Mac, the system verifies that the model file is NOT group- or world-accessible (0o077 mask) before loading.

## 2. Automated Permission Hardening
The `ConfigValidator` now automatically ensures that sensitive configuration and database files are properly protected.

### Automatic Correction
- **Target Files:** `.env`, `trades.db`, `audit.db`.
- **Logic:** If a sensitive file is detected to have insecure permissions (group- or world-accessible), the validator attempts to apply `chmod 600` (owner read/write only).
- **Reporting:** Success or failure of automated hardening is reported in the startup validation summary.

## 3. Security Verification
A new test suite `tests/test_security_mitigation.py` has been added to verify these mitigations:
- `test_regime_detector_load_path_validation`: Confirms models in untrusted paths are rejected.
- `test_regime_detector_load_path_bypass_attempt`: Confirms string-prefix path bypasses are blocked.
- `test_regime_detector_insecure_permissions`: Confirms models with loose permissions are rejected.
- `test_config_validator_auto_hardening`: Confirms insecure permissions are automatically fixed.
- `test_regime_detector_load_from_trusted_path`: Confirms legitimate models still load correctly.

## 4. Enhanced Secrets Masking in Logging
The `SecretMaskingProcessor` has been upgraded to prevent secret exposure in complex logging scenarios.

### Traceback and Stack Trace Redaction
- **Logic:** The masking processor is now positioned at the end of the `structlog` pipeline, ensuring it can scan and redact secrets from formatted tracebacks and stack traces.
- **Standard Library Support:** The `logging.Filter` implementation proactively formats and masks `exc_info` and `stack_info`, preventing leaks in standard Python logging output.
- **Deep Redaction:** The masker now recursively scans all log event data, including dictionaries and lists, to ensure nested secrets are protected.

## 5. Secure Interactive Setup
The guided setup wizard in `main.py` has been hardened to protect user credentials during configuration.

### Non-Echoing Input
- **Implementation:** Uses `getpass` for capturing the MetaAPI Token and MT5 Account Password.
- **Benefit:** Prevents sensitive credentials from being visible on the terminal screen or stored in shell history.

## 6. Logging Security Verification
A new test suite `tests/test_secret_masking_traceback.py` verifies the enhanced masking logic:
- `test_pydantic_secret_masking_direct`: Confirms Pydantic `SecretStr` objects are masked immediately.
- `test_logging_traceback_redaction`: Confirms secrets are removed from standard logging tracebacks.
- `test_logging_stack_info_redaction`: Confirms secrets are removed from stack traces.
- `test_structlog_traceback_redaction`: Confirms secrets are removed from `structlog` exception data.
- `test_proactive_exc_info_formatting`: Confirms `exc_info` is formatted and masked before output.

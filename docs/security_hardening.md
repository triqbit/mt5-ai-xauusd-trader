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

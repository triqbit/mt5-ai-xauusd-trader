# Security Hardening: File Permissions

## Overview
This document outlines the security requirements for file permissions within the MT5 AI Trading Bot environment. Ensuring restrictive permissions on sensitive files is critical for protecting broker credentials, trade history, and system audit trails.

## Sensitive Files
The following files are classified as sensitive and must have restrictive permissions:

- **`.env`**: Contains plaintext credentials including `MT5_PASSWORD`, `DATABASE_URL`, and `TELEGRAM_TOKEN`.
- **`trades.db`**: SQLite database containing execution history and account performance.
- **`audit.db`**: SQLite database containing system event logs and diagnostic data.

## Requirements (Linux/Mac)
On Unix-like systems, these files must not be world-readable. The recommended permission level is `0o600` (read/write for the owner only).

### Enforcement
The system's `ConfigValidator` automatically checks these permissions at startup. If a sensitive file is detected with insecure permissions (e.g., world-readable `0o644`), a warning will be issued in the startup diagnostics.

### Remediation
To fix permission issues, run the following command for each affected file:

```bash
chmod 600 .env
chmod 600 trades.db
chmod 600 audit.db
```

## Windows Compatibility
File permission checks are currently bypassed on Windows due to different permission models (ACLs). Operators on Windows should manually ensure that sensitive files are only accessible by the user account running the bot.

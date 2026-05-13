# Runbook 07: Secret Rotation Procedure
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

## Overview
Procedures for rotating sensitive credentials (MT5 Password, MetaAPI Token, Telegram Bot Token) safely to maintain system security and compliance.

## Step-by-Step Instructions

### 1. Preparation
1. **Identify the secret to rotate:**
   - `MT5_PASSWORD`: Broker account password.
   - `METAAPI_TOKEN`: MetaAPI developer portal token.
   - `TELEGRAM_TOKEN`: Telegram BotFather bot key.
   - `DATABASE_URL`: If using a remote SQL server (PostgreSQL/MySQL).
2. **Warn Stakeholders:** Notify the trading channel on Telegram that a brief maintenance restart will occur.

### 2. Update Provider & Local Config
1. **Rotate at Source:** Update the password or regenerate the token at the respective provider's portal.
2. **Update Production Environment:**
   ```bash
   # Edit the production .env file
   nano .env
   ```
   Replace the old secret with the new value. Ensure no leading/trailing spaces are present.
3. **Validate Config:** Run the environment validation script to ensure no placeholders or malformed strings remain:
   ```bash
   python scripts/validate_env.py
   ```
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_secret_rotation_initiated', 'Starting rotation of <SECRET_NAME>', datetime('now'));"
  ```

### 3. Apply & Verify
1. **Restart the Bot:**
   ```bash
   docker restart xauusd_trader
   ```
2. **Check Diagnostics:** Use the system doctor to verify the new credentials work:
   ```bash
   python scripts/doctor.py
   ```
3. **Verify Connectivity Logs:**
   ```bash
   # Look for successful connection messages
   docker logs xauusd_trader --tail 100 | grep -E "MT5|MetaAPI|Telegram"
   ```
4. **Smoke Test:**
   ```bash
   python scripts/smoke_test.py
   ```
5. **Readiness Check:**
   ```bash
   curl -f http://localhost:8000/health/readiness
   ```

### 4. Cleanup
1. **Old Secrets:** Ensure the old secret is revoked at the provider and cannot be used.
2. **Audit:** Verify the `audit.db` contains a record of the system restart following the credential change.
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_secret_rotation_completed', 'Successfully rotated <SECRET_NAME> and verified connectivity', datetime('now'));"
  ```

## Expected Outcomes
- New secrets are applied across the stack without downtime exceeding 2 minutes.
- No "Invalid Credentials", "401 Unauthorized", or "Authentication Failed" errors appear in logs.
- Connectivity to Broker, Cloud Gateway, and Alerting channels is successfully re-established.

## Escalation Path
1. **Security/Token Issues:** Security Lead (@xnessom).
2. **Access Blocked After Rotation:** Release Reliability Engineer (Jules03).
3. **Broker Portal Lockout:** Contact Broker Support.

## Verification Commands
```bash
python scripts/validate_env.py
python scripts/doctor.py
python scripts/smoke_test.py
```

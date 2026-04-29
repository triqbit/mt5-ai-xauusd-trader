# Runbook 07: Secret Rotation Procedure

## Description
This runbook standardizes the process for rotating sensitive API keys and credentials to maintain the security of the trading environment.

## Secrets to Rotate
- `MT5_PASSWORD`: Broker account password.
- `METAAPI_TOKEN`: MetaAPI cloud service token.
- `TELEGRAM_TOKEN`: BotFather token for the Telegram bot.
- `DATABASE_URL`: Connection string for production databases (if applicable).

---

## Rotation Procedure

### 1. Preparation
1.  Notify stakeholders of a brief maintenance window (if downtime is expected).
2.  Generate new credentials from the respective provider (Broker portal, MetaAPI dashboard, or @BotFather).

### 2. Execution
1.  Stop the trading bot (Docker or process).
2.  Open the `.env` file in the production environment.
3.  Update the relevant variables with the new values.
4.  **Security Check:** Ensure the old secrets are no longer present and that `.env` permissions are restricted:
    ```bash
    chmod 600 .env
    ```

### 3. Verification
1.  Start the trading bot.
2.  Monitor logs to ensure successful initialization:
    - MT5/MetaAPI: Look for "initialized successfully" or "fallback configured".
    - Telegram: Look for "Telegram bot initialized".
3.  Send a test message or wait for the next heartbeat to confirm Telegram connectivity.

### 4. Post-Rotation
1.  Revoke the old credentials in the provider's dashboard immediately.
2.  Confirm that the previous secrets no longer work by attempting a manual login (if applicable).

---

## Escalation Path
- **Loss of Access:** If new credentials do not work, contact the respective provider's support.
- **Security Breach:** If rotation is due to a suspected leak, escalate to the Security Lead (Jules02) for a full audit.

## Verification Commands
1. Check connectivity logs:
   ```bash
   grep -E "initialized|configured" logs/trading.log
   ```
2. Check `.env` file permissions:
   ```bash
   ls -l .env
   ```

# Runbook 07: Secret Rotation Procedure

## Overview
Regular rotation of credentials (MT5 login, Telegram tokens, DB secrets) is essential for maintaining enterprise-grade security.

## Rotation Schedule
- **MT5 Password:** Every 90 days.
- **Telegram Token:** Every 180 days (or immediately upon suspected leak).
- **Database Credentials:** Every 180 days.
- **Immediate Rotation:** Required if any credential is found in logs, public repos, or during a security breach.

## Procedures

### 1. MT5 Login Credentials
1.  **Change Password:** Log into the broker's member area or use the MT5 Terminal to change the trading account password.
2.  **Update Environment:** Update the `MT5_PASSWORD` in the production secret store (HashiCorp Vault, AWS Secrets Manager, or `.env` file).
3.  **Restart Bot:** Perform a rolling restart to pick up the new secret.
4.  **Verify:** Check logs for `INFO: MT5 connection established`.

### 2. Telegram Bot Token
1.  **Generate New Token:** Contact @BotFather on Telegram and use the `/token` command to rotate the API token.
2.  **Update Environment:** Update `TELEGRAM_TOKEN` in the secret store.
3.  **Restart Bot:** Perform a rolling restart.
4.  **Verify:** Run the connectivity test:
    ```python
    import telegram
    import asyncio
    bot = telegram.Bot(token="NEW_TOKEN")
    asyncio.run(bot.get_me())
    ```

### 3. Database Secrets
If using a managed PostgreSQL service:
1.  **Create New User:** Create a new DB user with identical permissions.
2.  **Update Config:** Update the bot's `DATABASE_URL` to use the new user.
3.  **Restart:** Restart the bot.
4.  **Revoke Old User:** Once the bot is successfully running with the new credentials, delete the old DB user.

## Security Verification
1.  **Check Logs:** Ensure no new secrets are accidentally being logged in plain text.
2.  **Gitleaks Scan:** Run a local secret scan to ensure no secrets were committed during the process:
    ```bash
    gitleaks detect --source . -v
    ```

## Escalation Path
1.  **Level 1:** Security Officer (@andonly1348) for secret management.
2.  **Level 2:** Broker Support for account lockout issues during rotation.

## Verification
- System continues to operate normally after rotation.
- No `Unauthorized` or `Login Failed` errors in logs.

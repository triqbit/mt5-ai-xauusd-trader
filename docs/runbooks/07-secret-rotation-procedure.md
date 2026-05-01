# Runbook 07: Secret Rotation Procedure

## Overview
This runbook describes the procedure for rotating critical secrets and API keys to maintain security hygiene or in response to a suspected leak.

## Scope
- MT5 Account Credentials (`MT5_PASSWORD`)
- MetaAPI Token (`METAAPI_TOKEN`)
- Telegram Bot Token (`TELEGRAM_TOKEN`)
- Database Credentials (`DATABASE_URL`)

## Rotation Schedule
- **Routine:** Every 90 days.
- **Emergency:** Immediately upon suspected compromise.

## Step-by-Step Rotation

### 1. MT5 Password Rotation
1. Log in to the Broker's client portal.
2. Change the trading account password.
3. Update the `.env` file on the production server:
   ```env
   MT5_PASSWORD="new_password_here"
   ```
4. Restart the bot: `docker restart mt5-trader`.

### 2. MetaAPI Token Rotation
1. Log in to the [MetaAPI Dashboard](https://app.metaapi.cloud/).
2. Generate a new API token.
3. Update production `.env`:
   ```env
   METAAPI_TOKEN="new_token_here"
   ```
4. Revoke the old token in the MetaAPI dashboard.
5. Restart the bot.

### 3. Telegram Bot Token Rotation
1. Open a chat with [@BotFather](https://t.me/botfather).
2. Use the `/revoke` command and select your bot.
3. Copy the new token provided.
4. Update production `.env`:
   ```env
   TELEGRAM_TOKEN="new_token_here"
   ```
5. Restart the bot.

### 4. GitHub Secrets Rotation (For CI/CD)
1. Go to Repository **Settings** > **Secrets and variables** > **Actions**.
2. Update the following secrets if they were changed:
   - `MT5_PASSWORD`
   - `TELEGRAM_TOKEN`
   - `DOCKERHUB_TOKEN`
3. Trigger a new `dry_run` release to verify the secrets work.

## Verification
1. Check logs for successful startup: `Application started`.
2. Verify MT5 connection: `Broker Connected`.
3. Send a test Telegram message: `System Health: Secret rotation verified`.

## Safety Guidelines
- **Never** commit secrets to the repository.
- Use a password manager to store and generate new secrets.
- Always revoke the old secret **after** verifying the new one works.

## Escalation Path
1. **Level 1:** Security Officer.
2. **Level 2:** DevOps Lead.

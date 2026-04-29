# Runbook 07: Secret Rotation Procedure

## Description
This runbook provides instructions for rotating secrets (MT5 credentials, MetaAPI tokens, Telegram tokens) safely.

## Rotation Procedures

### 1. MT5 Password Rotation
**Step-by-step Instructions:**
1. Change the password in the MetaTrader 5 Terminal or via the Broker's web portal.
2. Update the `MT5_PASSWORD` value in the production `.env` file or Secret Manager (e.g., Kubernetes Secrets, AWS Secrets Manager).
3. Restart the bot process to load the new configuration:
   ```bash
   kubectl rollout restart deployment/trading-bot
   ```
4. Verify logs for "Native MT5 SDK initialized successfully".

**Expected Outcome:** Bot connects using the new password.

### 2. MetaAPI Token Rotation
**Step-by-step Instructions:**
1. Generate a new token in the MetaAPI Dashboard.
2. Update `METAAPI_TOKEN` in the production configuration.
3. Restart the bot.
4. Verify fallback connectivity if applicable.

**Expected Outcome:** Bot initializes MetaAPI with the new token.

### 3. Telegram Bot Token Rotation
**Step-by-step Instructions:**
1. Use `@BotFather` on Telegram to revoke the old token and generate a new one.
2. Update `TELEGRAM_TOKEN` in the production configuration.
3. Restart the bot.
4. Trigger a test message or wait for the next heartbeat/trade to verify.

**Expected Outcome:** Telegram alerts continue to function.

## Security Best Practices
1. Never commit `.env` files to Git.
2. Use environment-specific secrets (Staging vs Production).
3. Rotate secrets immediately if a compromise is suspected or a team member leaves.
4. Use minimum-privilege tokens where possible.

## Escalation Path
1. Lockout after rotation: Contact Broker Support or MetaAPI Support.
2. Compromised secret: Immediate revocation and escalation to Security Officer (Jules02).

## Verification Commands
```bash
# Verify the bot is running after secret update
kubectl get pods
kubectl logs -f <pod_name> | grep "initializ"
```

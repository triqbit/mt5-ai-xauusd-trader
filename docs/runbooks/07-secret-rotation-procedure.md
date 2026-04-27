# Runbook 07: Secret Rotation Procedure

## Overview
This runbook details the process for rotating sensitive credentials (MT5, MetaAPI, Telegram, Database) without disrupting live trading operations.

## 1. Frequency
- **Routine**: Every 90 days.
- **Emergency**: Immediate rotation if a secret is leaked or a team member with access departs.

## 2. Rotation Procedures

### 2.1 MT5 Account Password
1. **Change at Broker**: Use the broker's portal or MT5 desktop terminal to change the master password.
2. **Update `.env`**: Update `MT5_PASSWORD` in the production environment variables.
3. **Graceful Restart**: Restart the bot to use the new credentials. Note: Existing open positions will be picked up by the ticket ID.

### 2.2 MetaAPI Token
1. **Generate New Token**: Log into the MetaAPI dashboard and generate a new API token.
2. **Update Environment**: Update `METAAPI_TOKEN` in the production configuration.
3. **Restart Bot**: Trigger a restart to re-initialize the MetaAPI connection.
4. **Revoke Old Token**: Once the bot is confirmed stable with the new token, delete the old one from the MetaAPI dashboard.

### 2.3 Database Credentials
1. **Update DB User**: Change the password for the `trader` user in PostgreSQL/MySQL.
2. **Update Connection String**: Update `DATABASE_URL` in `.env`.
3. **Restart Bot**: The bot will reconnect on startup.

### 2.4 Telegram Bot Token
1. **BotFather**: Use `@BotFather` on Telegram to revoke and generate a new token.
2. **Update Environment**: Update `TELEGRAM_TOKEN`.
3. **Restart Bot**: Verify alerts are still being received.

## 3. Best Practices
- **No Hardcoding**: Never commit secrets to Git.
- **Verification**: Always verify the bot connects successfully after rotation.
- **Overlap**: If possible, keep the old secret valid for a 5-minute overlap until the new one is confirmed working.

## 4. Escalation Path
- **P2 (Scheduled Rotation)**: Perform during low volatility or weekend.
- **P1 (Compromised Secret)**: Rotate immediately, regardless of market conditions.

## 5. Verification Commands
```bash
# Check if the bot successfully initialized after secret update
grep "Configuration loaded" logs/trading_bot.log | tail -n 1
grep "MT5 connector initialized successfully" logs/trading_bot.log | tail -n 1
```

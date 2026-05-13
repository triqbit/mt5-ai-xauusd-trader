# Runbook 02: MT5 Connection Outage
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

## Overview
Procedures for diagnosing and recovering from connection loss between the bot and MetaTrader 5 or MetaAPI.

## Step-by-Step Instructions

### 1. Identify Connection State
Check the logs for connection errors:
```bash
docker logs xauusd_trader --tail 100 | grep -E "MT5|MetaAPI"
```
Common errors:
- `Connection failed: terminal not found`: Check `MT5_PATH` in `.env`.
- `Login failed: invalid credentials`: Check `MT5_LOGIN` and `MT5_PASSWORD`.
- `MetaAPI: 401 Unauthorized`: Check `METAAPI_TOKEN`.

### 2. Terminal Health Check
If running locally or via Wine:
1. Ensure the MT5 Terminal application is open and logged into the correct account.
2. Verify "Algo Trading" is enabled (button is green).
3. Ensure the symbol `XAUUSD` is present in the Market Watch.

### 3. Manual Reconnection
Restart the bot to trigger a clean initialization:
```bash
docker restart xauusd_trader
```

### 4. Failover Management
If native MT5 connection is unstable and MetaAPI is configured:
1. The bot will automatically attempt failover if `METAAPI_TOKEN` is present.
2. Monitor logs to confirm "Connected via MetaAPI cloud gateway".

## Expected Outcomes
- Logs show "Successfully connected to MT5".
- `HealthChecker` reports `mt5` component as `healthy`.
- Live tick data begins flowing in the console/dashboard.

## Escalation Path
1. **Persistent Auth Errors:** Broker Support.
2. **MetaAPI Outage:** MetaAPI Status Page / Support.
3. **Internal Connector Bugs:** Jules01 (Trading Lead).

## Verification Commands
```bash
python scripts/doctor.py
curl -s http://localhost:8000/health/readiness
```

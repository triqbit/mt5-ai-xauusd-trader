# Runbook 02: MT5 Connection Outage

## Overview
This runbook details the response procedure for connection failures between the trading bot and the MetaTrader 5 (MT5) terminal or MetaAPI cloud gateway.

## Symptoms
- **Telegram Alert:** `Broker Connection Lost` (P0/P1)
- **Logs:** `MT5 connection failed`, `Terminal not found`, or `MetaAPI connection timeout`.
- **Health Check:** `/health/readiness` returns 503 or `MT5: FAILED`.

## Diagnostic Steps

### 1. Run Automated Diagnostics
Execute the bot "doctor" script to identify connectivity and environment issues:
```bash
python scripts/doctor.py
```

### 2. Common Log Patterns
Search for these patterns to pinpoint the failure:
- `MT5 terminal not found`: Incorrect `MT5_PATH` or terminal not running.
- `MT5 login failed`: Check `MT5_LOGIN` and `MT5_PASSWORD`.
- `MetaAPI connection timeout`: Network issue or invalid `METAAPI_TOKEN`.
- `Market closed`: Attempting to trade during weekends or holidays.

### 3. Check MT5 Terminal Status
- **Local Mode (Windows):**
  1. Verify if the MT5 Terminal is running on the host machine.
  2. Check the `Journal` tab in the MT5 Terminal for broker-side authentication errors.
  3. Verify account login status (green/blue icon in the bottom right corner).
- **Cloud Mode (MetaAPI):**
  1. Check [MetaAPI Status Page](https://status.metaapi.cloud/).
  2. Verify that the MetaAPI account is in "CONNECTED" status in the MetaAPI Dashboard.

## Recovery Procedures

### Scenario A: Local Terminal Crash
1. **Restart the MT5 Terminal:**
   ```powershell
   # On Windows
   Stop-Process -Name "terminal64" -ErrorAction SilentlyContinue
   Start-Process "C:\Program Files\MetaTrader 5\terminal64.exe"
   ```
2. The bot should automatically attempt to reconnect on the next heartbeat.

### Scenario B: MetaAPI Gateway Issue
1. Force a reconnect by restarting the bot container:
   ```bash
   docker restart mt5-trader
   ```
2. If issues persist, verify the `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in the `.env` file.

### Scenario C: Broker Maintenance
1. Check the broker's website or portal for scheduled maintenance.
2. If maintenance is confirmed, the bot should be allowed to stay in a retry loop, or shut down to prevent logic errors.

## Fallback Protocol
If MT5 remains unreachable for >15 minutes during market hours:
1. **Manual Intervention:** Use the MT5 mobile app to monitor and manage open positions.
2. **Emergency Stop:** Stop the bot process to prevent unintended execution if the connection flickers.
   ```bash
   docker stop mt5-trader
   ```

## Expected Outcomes
- `scripts/doctor.py` shows all connectivity checks as `PASSED`.
- `/health/readiness` returns a 200 OK response with `MT5: HEALTHY`.
- Real-time price data (ticks) resumes in the logs.

## Verification Commands
- **Check Health API:** `curl http://localhost:8000/health/readiness`
- **Verify Connections:** `python scripts/doctor.py`
- **Tail Logs:** `docker logs -f mt5-trader | grep -E "MT5|MetaAPI"`

## Escalation Path
1. **Level 1:** Trading Operations (@maintainer-trading).
2. **Level 2:** Release Reliability Engineer (Jules03 - @andonly1348).
3. **Level 3:** Broker Support.

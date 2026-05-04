# Runbook 02: MT5 Connection Outage

## Overview
This runbook details the response procedure for connection failures between the trading bot and the MetaTrader 5 (MT5) terminal or MetaAPI cloud gateway.

## Symptoms
- Telegram Alert: `Broker Connection Lost` (P0/P1)
- Logs: `MT5 connection failed`, `Terminal not found`, or `MetaAPI connection timeout`.
- Health Check: `/health/readiness` returns 503 or `MT5: FAILED`.

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

### 3. Check Local MT5 Terminal (Windows Execution)
1. Verify if the MT5 Terminal is running on the host machine.
2. Check the `Journal` tab in the MT5 Terminal for broker-side authentication errors (e.g., `Invalid account`).
3. Verify account login status (green/blue icon in the bottom right corner).

### 4. Verify Configuration
Check `.env` via `scripts/validate_env.py` to ensure credentials are correct:
- `MT5_LOGIN`
- `MT5_SERVER`
- `MT5_PASSWORD`

### 5. Network Connectivity
1. Ping the broker's server address (found in MT5 terminal properties).
2. Verify that `MT5_PATH` in `src/core/config.py` correctly points to the `terminal64.exe`.

## Recovery Procedures

### Scenario A: Local Terminal Crash
1. Restart the MT5 Terminal:
   ```powershell
   # On Windows
   Stop-Process -Name "terminal64" -ErrorAction SilentlyContinue
   Start-Process "C:\Program Files\MetaTrader 5\terminal64.exe"
   ```
2. The bot should automatically attempt to reconnect on the next heartbeat.

### Scenario B: MetaAPI Gateway Issue (Cloud Mode)
1. Check [MetaAPI Status Page](https://status.metaapi.cloud/).
2. Force a reconnect by restarting the container:
   ```bash
   docker restart mt5-trader
   ```

### Scenario C: Broker Maintenance
1. Check the broker's website or portal for scheduled maintenance.
2. If maintenance is confirmed, set `MODE=backtest` or shut down the bot to prevent logic errors.

## Fallback Protocol
If MT5 remains unreachable for >15 minutes during market hours:
1. **Manual Intervention:** Use the MT5 mobile app to monitor and manage open positions.
2. **Emergency Stop:** Stop the bot process to prevent unintended execution if the connection flickers.

## Expected Outcomes
- `scripts/doctor.py` shows all connectivity checks as `PASSED`.
- `/health/readiness` returns a 200 OK response with `MT5: HEALTHY`.
- Real-time price data (ticks) resumes in the logs.

## Verification Commands
- **Check Health API:** `curl http://localhost:8000/health/readiness`
- **Tail Logs:** `tail -f logs/trading_bot.log | grep -E "MT5|MetaAPI"`
- **Verify Connections:** `python scripts/doctor.py`

## Escalation Path
1. **Level 1:** Trading Operations (@maintainer-trading).
2. **Level 2:** Infrastructure / Release Reliability (Jules03).
3. **Level 3:** Broker Support.

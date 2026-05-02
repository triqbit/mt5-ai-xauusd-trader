# Runbook 02: MT5 Connection Outage

## Overview
This runbook details the response procedure for connection failures between the trading bot and the MetaTrader 5 (MT5) terminal or MetaAPI cloud gateway.

## Symptoms
- Telegram Alert: `Broker Connection Lost` (P0/P1)
- Logs: `MT5 connection failed`, `Terminal not found`, or `MetaAPI connection timeout`.
- Trading halted or orders rejected.

## Diagnostic Steps

### 1. Check Local MT5 Terminal (If using local execution)
1. Verify if the MT5 Terminal is running on the host machine.
2. Check the `Journal` tab in the MT5 Terminal for connection errors.
3. Verify account login status (green icon in bottom right).

### 2. Verify Credentials
Check `.env` or environment variables:
- `MT5_LOGIN`
- `MT5_SERVER`
- `MT5_PASSWORD`

### 3. Network Connectivity
1. Ping the broker's server address.
2. Check for firewall rules blocking the MT5 terminal or Python process.

## Recovery Procedures

### Scenario A: Local Terminal Crash
1. Restart the MT5 Terminal:
   ```powershell
   # If on Windows
   Restart-Process -Name "terminal64"
   ```
2. The bot should automatically attempt to reconnect on the next heartbeat.

### Scenario B: MetaAPI Gateway Issue (Cloud Fallback)
1. Check [MetaAPI Status Page](https://status.metaapi.cloud/).
2. Verify `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`.
3. Force a reconnect by restarting the bot service:
   ```bash
   docker restart mt5-trader
   ```

### Scenario C: Broker Maintenance
1. Check broker website for scheduled maintenance.
2. If maintenance is confirmed, pause the bot until the window ends.

## Fallback Protocol
If MT5 remains unreachable for >15 minutes:
1. **Manual Intervention:** Use a mobile MT5 app to monitor and manage open positions.
2. **Emergency Stop:** Set `MODE=backtest` or shut down the bot to prevent unintended trades once connection is restored.

## Expected Outcomes
- Bot successfully initializes and connects to the MT5 terminal or MetaAPI.
- Trading activity resumes (if market is open and signals are valid).
- Real-time price data starts flowing into the application.

## Verification Commands
- **Check Health API:** `curl http://localhost:8000/health/readiness`
- **Tail Logs:** `tail -n 50 trading_bot.log | grep -E "MT5|MetaAPI"`
- **Docker Status:** `docker ps | grep mt5-trader`

## Escalation Path
1. **Level 1:** Trading Operations.
2. **Level 2:** Infrastructure / DevOps.
3. **Level 3:** Broker Support.

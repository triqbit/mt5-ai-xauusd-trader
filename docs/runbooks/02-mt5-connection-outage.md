# Runbook 02: MT5 Connection Outage

## Overview
This runbook describes the procedure for responding to connection failures between the trading bot and the MetaTrader 5 (MT5) platform or MetaAPI services.

## Diagnosis

### Symptoms
- Telegram Alert: `CRITICAL: MT5 Connection Failed`
- Logs: `ERROR: Failed to connect to MT5 terminal`
- Monitoring: Heartbeat missing for > 60 seconds.

### Check Commands
1.  **Check Terminal Status:** Verify the MT5 terminal is running on the host machine/container.
2.  **Verify Credentials:**
    ```bash
    echo $MT5_LOGIN
    echo $MT5_SERVER
    ```
3.  **Connectivity Test:**
    ```bash
    ping <mt5-server-address>
    ```

## Recovery Steps

### 1. Automated Restart
If running in Docker, restart the container:
```bash
docker restart trading-bot
```

### 2. Manual Terminal Restart
If running on a Windows VPS/Local machine:
1.  Close the MetaTrader 5 terminal.
2.  Ensure no zombie processes remain: `taskkill /F /IM metatester64.exe /T` (if applicable).
3.  Re-open MetaTrader 5.
4.  Ensure "Auto Trading" is enabled in the terminal toolbar.

### 3. Credential Verification
1.  Check if the account password has expired or been changed.
2.  Update the `.env` file with correct `MT5_PASSWORD`.
3.  Restart the bot.

### 4. Network/Broker Issues
1.  Check the broker's status page (if available).
2.  Switch to a different MT5 server (e.g., a backup access point) in the MT5 terminal settings.

## Forensic Analysis
- Check `logs/trading.log` for the specific error code returned by MT5 (e.g., `RES_E_INVALID_ACCOUNT`, `RES_E_NETWORK_PROBLEM`).
- Inspect MT5 Terminal "Journal" tab for platform-level errors.

## Escalation Path
1.  **Level 1:** On-call Trader (@maintainer-trading) to check broker status.
2.  **Level 2:** Systems Administrator for network/VPS issues.
3.  **Level 3:** Broker Support for account-level lockouts.

## Verification
- Log message: `INFO: MT5 connection established`
- Monitor shows active heartbeat and updated equity data.

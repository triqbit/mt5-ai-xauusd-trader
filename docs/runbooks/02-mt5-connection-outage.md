# Runbook 02: MT5 Connection Outage

## Description
This runbook provides steps to diagnose and recover from connection failures between the trading bot and MetaTrader 5 or the MetaAPI cloud service.

## Failure Scenarios

### 1. Native MT5 SDK Connection Failure (Windows)
**Symptoms:** Logs show "Native mt5.initialize failed" or "Native MT5 initialization error".
**Cause:** MT5 terminal not running, incorrect path, wrong credentials, or network issues.

**Steps to Recover:**
1.  Ensure the MetaTrader 5 terminal is installed at the path specified in `.env` (`MT5_PATH`).
2.  Open the MT5 terminal manually and verify you can log in to the account.
3.  Check if "Algo Trading" is enabled in the MT5 terminal (top toolbar).
4.  Verify `.env` credentials: `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`.
5.  Check system logs for local network or firewall issues blocking the terminal.
6.  Restart the MT5 terminal and then restart the bot.

**Expected Outcome:** Logs show "Native MT5 SDK initialized successfully."

---

### 2. MetaAPI Fallback Connection Failure (Linux/Mac/Cloud)
**Symptoms:** Logs show "MetaAPI initialization failed" or "All MT5 connection paths failed."
**Cause:** Invalid `METAAPI_TOKEN`, invalid `METAAPI_ACCOUNT_ID`, or MetaAPI service outage.

**Steps to Recover:**
1.  Log in to the [MetaAPI Dashboard](https://app.metaapi.cloud/).
2.  Verify the `METAAPI_TOKEN` is valid and hasn't expired.
3.  Ensure the MetaAPI account is in "CONNECTED" status on the dashboard.
4.  Check for service outages on the MetaAPI status page.
5.  Verify the credentials in `.env`: `METAAPI_TOKEN`, `METAAPI_ACCOUNT_ID`.
6.  Test the API connection using a simple `curl` request to the MetaAPI endpoint (refer to MetaAPI docs).

**Expected Outcome:** Logs show "MetaAPI fallback configured."

---

## Escalation Path
- **Credential Issues:** Contact the Account Administrator.
- **Service Outage:** Check MetaAPI or Broker status pages.
- **Persistent SDK Issues:** Escalate to the Technical Lead (Jules01).

## Verification Commands
1. Check bot logs for connectivity status:
   ```bash
   grep -i "MT5 connector" logs/trading.log
   ```
2. Verify MT5 process is running (Windows):
   ```powershell
   Get-Process -Name "terminal64"
   ```
3. Check network connectivity to broker server (replace with your server address):
   ```bash
   ping <MT5_SERVER_ADDRESS>
   ```

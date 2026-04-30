# Runbook 02: MT5 Connection Outage

## Description
This runbook provides instructions for handling failures in MT5 terminal connection or MetaAPI cloud fallback.

## Troubleshooting Steps

### 1. Verify Native MT5 Connection (Windows)
**Step-by-step Instructions:**
1. Check if the MT5 Terminal is running on the host machine.
2. Verify `MT5_PATH` in `.env` matches the installation path.
3. Check `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` credentials.
4. Check MT5 "Journal" tab for connection errors (e.g., "Invalid account", "No connection").
5. Test connection with a minimal script:
   ```python
   import MetaTrader5 as mt5
   if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
       print("Failed:", mt5.last_error())
   else:
       print("Connected")
       mt5.shutdown()
   ```

**Expected Outcome:** `mt5.initialize()` returns `True`.

### 2. Verify MetaAPI Fallback (Linux/Mac/Cloud)
**Step-by-step Instructions:**
1. Check `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in `.env`.
2. Verify internet connectivity to MetaAPI endpoints.
3. Check MetaAPI dashboard for account status (should be `DEPLOYED`).
4. Check logs for "MetaAPI initialization failed".

**Expected Outcome:** Logs show "MetaAPI fallback configured".

### 3. Check Network Connectivity
**Step-by-step Instructions:**
1. Ping the broker's MT5 server address.
2. Ensure firewall allows outgoing traffic on MT5 ports (usually 443 or specific broker ports).
3. Check for ISP or Data Center outages.

**Expected Outcome:** Successful ping and open ports.

## Escalation Path
1. Credentials invalid: Contact Broker Support.
2. MT5 Terminal crash: Restart Terminal/Server.
3. MetaAPI platform issue: Check [MetaAPI Status Page](https://status.metaapi.cloud).
4. Persistent connection loss: Escalate to Trading Lead (Jules01).

## Verification Commands
```bash
# Check bot logs for connection status
grep "MT5" logs/app.log

# Check environment variables
echo $MT5_SERVER
echo $MT5_LOGIN
```

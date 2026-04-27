# Runbook 02: MT5 Connection Outage

## Overview
This runbook describes the procedure for handling connection outages between the trading bot and the MetaTrader 5 terminal or the MetaAPI cloud service.

## 1. Failure Identification
Connection issues are identified by:
- `MT5Connector` logging "Native mt5.initialize failed" or "All MT5 connection paths failed".
- Telegram alerts regarding "Broker Connection Lost".
- Empty OHLCV dataframes returned by `get_ohlcv`.

## 2. Recovery Procedures

### 2.1 Native MT5 SDK Outage (Windows)
1. **Check MT5 Terminal**: Ensure the MetaTrader 5 terminal is running on the host machine.
2. **Check Credentials**: Verify `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` in the `.env` file.
3. **Network Check**: Ensure the host has internet access and can reach the broker's server.
4. **Restart Terminal**: Close and reopen the MT5 terminal.
5. **Restart Bot**: Restart the trading bot process to trigger a new initialization attempt.

### 2.2 MetaAPI Fallback Activation (Linux/Cloud)
The bot is designed to use MetaAPI if the native SDK is unavailable.
1. **Verify Token**: Ensure `METAAPI_TOKEN` is correctly set in environment variables.
2. **Account ID**: Ensure `METAAPI_ACCOUNT_ID` is correct.
3. **Check MetaAPI Status**: Visit the MetaAPI status page to check for service-wide outages.
4. **API Limits**: Check if the MetaAPI account has reached its request limits.

### 2.3 Permanent Outage Protocol
If connection cannot be restored within 10 minutes:
1. **Manual Intervention**: Log into the MT5 mobile app or another terminal instance.
2. **Close Positions**: If the market is volatile and the bot is unable to manage trades, consider closing open positions manually to protect capital.
3. **Stop Bot**: Kill the bot process to prevent erratic behavior upon partial reconnection.

## 3. Escalation Path
- **P2 (Single Reconnection Failure)**: Monitor for automatic retry.
- **P1 (Persistent Connection Outage > 5 min)**: Immediate investigation required. Contact broker support if network/credentials are verified.

## 4. Verification Commands
```bash
# Check bot logs for connection status
tail -f logs/trading_bot.log | grep "MT5 connector"

# Verify environment variables (ensure no secrets are logged in production)
echo $MT5_SERVER
echo $MT5_LOGIN
```

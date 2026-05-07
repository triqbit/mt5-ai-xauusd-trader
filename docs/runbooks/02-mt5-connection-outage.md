# Runbook 02: MT5 Connection Outage
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Procedures for resolving connection failures between the trading bot and MetaTrader 5 (MT5) or MetaAPI.

## Step-by-Step Instructions

### 1. Diagnose Connectivity
- Run the system doctor: `python scripts/doctor.py`.
- Check if `.env` has correct `MT5_LOGIN`, `MT5_SERVER`, and `MT5_PASSWORD`.

### 2. Recover Local MT5 (Windows)
- Ensure MT5 Terminal is running.
- Check MT5 `Journal` for "Invalid Account" or "No Connection".
- Restart Terminal if frozen.

### 3. Recover MetaAPI (Cloud)
- Verify `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`.
- Check MetaAPI status page: `https://status.metaapi.cloud/`.
- Restart container: `docker restart mt5-trader`.

## Expected Outcomes
- `scripts/doctor.py` reports `PASSED` for connectivity.
- Logs show active price ticks for `XAUUSD`.
- Readiness probe `/health/readiness` returns `200 OK`.

## Verification Commands
- `python scripts/doctor.py`
- `curl http://localhost:8000/health/readiness`
- `docker logs mt5-trader --tail 50 | grep "MT5"`

## Escalation Path
1. **Connectivity Issues:** Trading Ops (@maintainer-trading).
2. **Platform Stability:** Jules03 (@andonly1348).
3. **Broker Issues:** Contact Broker Support via Portal.

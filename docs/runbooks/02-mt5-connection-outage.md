# Runbook 02: MT5 Connection Outage
**Version:** 1.3 | **Last Updated:** 2024-05-22

## Overview
Procedures for resolving connection failures between the trading bot and MetaTrader 5 (MT5) or the MetaAPI cloud gateway.

## Step-by-Step Instructions

### 1. Diagnose Connectivity
- Run the system doctor: `python scripts/doctor.py`. This script checks connectivity to the database, Redis, and validates MT5/MetaAPI configuration.
- Check logs for specific error patterns:
  - `Failed to connect to MetaTrader 5` -> Local MT5 issue.
  - `MetaAPI error: 401 Unauthorized` -> Token rotation needed.
  - `MetaAPI error: 503 Service Unavailable` -> Cloud outage.
- Verify environment variables in `.env`: `MT5_LOGIN`, `MT5_SERVER`, `MT5_PASSWORD`, `METAAPI_TOKEN`, `METAAPI_ACCOUNT_ID`.
- Run the environment validation gate: `python scripts/validate_env.py`

### 2. Recover Local MT5 (Windows Environment)
- Ensure the MT5 Terminal application is running.
- Check the MT5 `Journal` tab for:
  - "Invalid Account" -> Credentials error.
  - "No Connection" -> Network or Broker server issue.
- If the terminal is frozen, restart the application.
- Verify that "Algo Trading" is enabled (Green icon) in the top toolbar.

### 3. Recover MetaAPI (Cloud Gateway)
- Verify `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` are valid in the MetaAPI Dashboard.
- Check MetaAPI status: `https://status.metaapi.cloud/`.
- If using Docker, restart the container to force a reconnection:
  ```bash
  docker restart xauusd_trader
  ```
- Monitor logs to ensure the provisioning process completes:
  ```bash
  docker logs xauusd_trader --tail 100 | grep -E "MT5|MetaAPI"
  ```

### 4. Connection Stability Check
- Once reconnected, verify price flow:
  ```bash
  # Check if the readiness probe returns 200 OK
  curl -f http://localhost:8000/health/readiness
  ```
- Ensure `MT5_CONNECTION_STATUS` in Prometheus metrics is `1.0`:
  ```bash
  curl -s http://localhost:8000/metrics | grep mt5_connection_status
  ```
- Run a smoke test to verify all dependencies:
  ```bash
  python scripts/smoke_test.py
  ```

## Expected Outcomes
- `scripts/doctor.py` reports `PASSED` for all connectivity checks.
- Application logs show active price updates for `XAUUSD`.
- The readiness probe `/health/readiness` returns a `200 OK` status.

## Verification Commands
- `python scripts/doctor.py`
- `python scripts/validate_env.py`
- `python scripts/smoke_test.py`
- `curl -i http://localhost:8000/health/readiness`
- `docker logs xauusd_trader --tail 50`

## Escalation Path
1. **Trading Connectivity:** Trading Ops (@maintainer-trading).
2. **Platform Stability:** Release Reliability Engineer (Jules03).
3. **Broker Issues:** Contact Broker Support via the Client Portal.

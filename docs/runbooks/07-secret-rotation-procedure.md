# Runbook 07: Secret Rotation Procedure
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Procedures for rotating `MT5_PASSWORD`, `METAAPI_TOKEN`, and `TELEGRAM_TOKEN`.

## Step-by-Step Instructions

### 1. Rotate & Update
- Update secret at provider (Broker, MetaAPI, Telegram).
- Replace value in production `.env`.

### 2. Verify & Restart
- Run `python scripts/validate_env.py` to check for placeholder strings.
- Restart: `docker restart mt5-trader`.
- Check connectivity: `python scripts/doctor.py`.

## Expected Outcomes
- New secrets applied and old ones revoked.
- No "Invalid Credentials" errors in logs.
- Connections successfully re-established.

## Verification Commands
- `python scripts/validate_env.py`
- `python scripts/doctor.py`
- `curl http://localhost:8000/health/readiness`

## Escalation Path
1. **Security/Locker Issues:** @xnessom.
2. **Access Blocked:** Release Reliability Engineer (Jules03).

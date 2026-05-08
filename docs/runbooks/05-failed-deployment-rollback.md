# Runbook 05: Failed Deployment Rollback
**Version:** 1.2 | **Last Updated:** 2026-05-08

## Overview
Safe procedures for reverting a "bad" release. This covers reverting Docker images, rolling back database schema migrations (Alembic), and restoring environment configuration.

## Step-by-Step Instructions

### 1. Stop the Failing Release
Immediately stop the current container to prevent further errors or capital risk:
```bash
docker stop xauusd_trader
```

### 2. Revert Docker Container
Identify the last known stable version (e.g., `v1.1.0-rc3`) from the deployment logs or GitHub Release page.
1. **Pull the stable image:**
   ```bash
   docker pull triqbit/mt5-ai-xauusd-trader:v1.1.0-rc3
   ```
2. **Update the environment file:**
   Set `BOT_VERSION=v1.1.0-rc3` in `.env`.
3. **Restart the stack:**
   ```bash
   docker-compose up -d
   ```

### 3. Downgrade Database Schema (If Necessary)
If the failed release included database migrations (Alembic), you must downgrade the schema to match the code version.
1. **Identify current and target revisions:**
   ```bash
   # See current revision
   docker exec -it xauusd_trader alembic current
   # See history to find the previous revision ID
   docker exec -it xauusd_trader alembic history
   ```
2. **Execute downgrade:**
   ```bash
   docker exec -it xauusd_trader alembic downgrade <previous_revision_id>
   ```
   *Note: Ensure you have a database backup (Runbook 04) before performing downgrades.*

### 4. Restoration of Configuration
If the release failure was due to invalid environment variables:
1. Revert `.env` to the last known good state from the secure backup.
2. Run the validation gate: `python scripts/validate_env.py`.

### 5. Verification
- Verify the container is running the correct version:
  ```bash
  docker inspect xauusd_trader --format '{{.Config.Labels.version}}'
  ```
- Check the liveness and readiness probes:
  ```bash
  curl -f http://localhost:8000/health/liveness
  curl -f http://localhost:8000/health/readiness
  ```
- Monitor the audit trail for "System Startup" events.

## Expected Outcomes
- The system is restored to a previous stable state (Code + Schema + Config).
- High-severity (P0/P1) alerts triggered by the failed deployment are resolved.
- Database schema consistency is maintained.

## Verification Commands
- `docker ps | grep xauusd_trader`
- `docker exec -it xauusd_trader alembic current`
- `python scripts/smoke_test.py`
- `curl -s http://localhost:8000/metrics | grep system_version`

## Escalation Path
1. **Rollback Execution Help:** Release Engineer (Jules03).
2. **Data/Migration Issues:** Lead Developer (@maintainer-quality).
3. **Incident Post-Mortem:** Engineering Lead.

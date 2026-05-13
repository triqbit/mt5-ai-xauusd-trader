# Runbook 05: Failed Deployment Rollback
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

## Overview
Standard procedures for rolling back the production environment to a last known stable state following a failed deployment. Aligned with the [Release Playbook](../RELEASE_PLAYBOOK.md).

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
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_rollback_initiated', 'Rolling back to version v1.1.0-rc3 due to deployment failure', datetime('now'));"
  ```

### 3. Downgrade Database Schema (If Necessary)
If the failed release included database migrations (Alembic), you must downgrade the schema to match the code version.
1. **Verify Migration Reversibility:**
   Run the migration verification script in a safe environment if possible:
   ```bash
   python scripts/verify_migrations.py
   ```
2. **Identify current and target revisions:**
   ```bash
   # See current revision
   docker exec -it xauusd_trader alembic current
   # See history to find the previous revision ID
   docker exec -it xauusd_trader alembic history
   ```
3. **Execute downgrade:**
   ```bash
   docker exec -it xauusd_trader alembic downgrade <previous_revision_id>
   ```
   *Note: Ensure you have a database backup (Runbook 04) before performing downgrades.*
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_db_migration_downgrade', 'Downgraded database schema to revision <previous_revision_id>', datetime('now'));"
  ```

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
- Run the smoke test suite to ensure stability:
  ```bash
  python scripts/smoke_test.py
  ```
- Monitor the audit trail for "System Startup" events.
- **Audit Manual Action:**
  ```bash
  sqlite3 audit.db "INSERT INTO audit_log (actor, action, details, created_at) VALUES ('operator', 'operator_rollback_verified', 'Rollback to v1.1.0-rc3 verified and stable', datetime('now'));"
  ```

## Expected Outcomes
- The system is restored to a previous stable state (Code + Schema + Config).
- High-severity (P0/P1) alerts triggered by the failed deployment are resolved.
- Database schema consistency is maintained.

## Escalation Path
1. **Rollback Execution Help:** Release Engineer (Jules03).
2. **Data/Migration Issues:** Lead Developer (@maintainer-quality).
3. **Incident Post-Mortem:** Engineering Lead.

## Verification Commands
```bash
docker ps | grep xauusd_trader
docker exec -it xauusd_trader alembic current
python scripts/smoke_test.py
```

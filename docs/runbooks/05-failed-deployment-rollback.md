# Runbook 05: Failed Deployment Rollback

## Overview
This runbook provides instructions for rolling back a bad release, including Docker containers and database migrations.

## Rollback Triggers
- High error rate immediately after deployment.
- Critical functionality broken (e.g., cannot connect to MT5).
- Unexpected trading behavior.
- Security vulnerability discovered in production image.

## Step-by-Step Rollback

### 1. Identify Last Stable Version
Check the `CHANGELOG.md` or the GitHub Releases page to find the previous stable tag (e.g., `v1.2.2`).

### 2. Roll Back Docker Deployment
If using Docker Compose:
1. Update `docker-compose.yml` image tag or set environment variable:
   ```bash
   export BOT_VERSION=v1.2.2
   docker-compose up -d
   ```
2. Or pull and run the previous image directly:
   ```bash
   docker pull triqbit/mt5-trader:v1.2.2
   docker stop mt5-trader
   docker run -d --name mt5-trader triqbit/mt5-trader:v1.2.2
   ```

### 3. Roll Back Database Migrations (If necessary)
If the new release included a database schema change that is incompatible with the old version:
1. Identify the target migration revision (found in `migrations/versions/`).
2. Run Alembic downgrade:
   ```bash
   alembic downgrade <previous_revision_id>
   ```
   *Note: Be careful with `downgrade`, as it may result in data loss for newly added columns.*

### 4. Revert Git Main Branch (Optional)
If the release was tagged on `main`, revert the PR or commit that introduced the failure to keep `main` stable.

## Post-Rollback Tasks
1. Verify system health and monitoring dashboards.
2. Communicate the rollback to stakeholders.
3. Perform a Root Cause Analysis (RCA) before attempting to re-deploy.

## Verification
- Run health check: `curl http://localhost:8000/health` (if implemented).
- Check logs for: `Application started - Version: v1.2.2`.

## Escalation Path
1. **Level 1:** Release Engineer (Jules03).
2. **Level 2:** Core Maintainers.

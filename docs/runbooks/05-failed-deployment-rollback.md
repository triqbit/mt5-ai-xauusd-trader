# Runbook 05: Failed Deployment Rollback
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Safe procedures for reverting a bad release, including Docker images and database migrations.

## Step-by-Step Instructions

### 1. Revert Container
- Identify stable tag (e.g., `v1.2.2`).
- Update deployment env: `export BOT_VERSION=v1.2.2 && docker-compose up -d`.

### 2. Downgrade Database (If Needed)
- Find current revision: `alembic current`.
- Downgrade to last known good: `alembic downgrade <revision>`.

## Expected Outcomes
- System runs on previous stable version.
- P0/P1 alerts triggered by the release are resolved.
- Database schema matches the binary/container version.

## Verification Commands
- `docker inspect mt5-trader --format '{{.Config.Labels.version}}'`
- `alembic current`
- `curl http://localhost:8000/health/liveness`

## Escalation Path
1. **Rollback Help:** Release Engineer (Jules03).
2. **Post-Mortem:** Engineering Lead (@maintainer-quality).

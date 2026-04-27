# Runbook 05: Failed Deployment Rollback

## Overview
This runbook defines the rollback procedure for a bad release of the trading bot. Speed is critical to minimize exposure to buggy trading logic.

## 1. Rollback Triggers
Roll back immediately if:
- **Crash Loop**: The bot fails to stay running for more than 1 minute.
- **Erratic Trading**: Large number of rejected orders or incorrect position sizing.
- **Connectivity**: Unable to connect to MT5 with verified credentials.
- **Critical Alerts**: P1 alerts triggered immediately post-deployment.

## 2. Rollback Procedures

### 2.1 Docker-based Deployment
1. **Identify Previous Tag**: Find the last known stable image tag (e.g., `v1.1.0`).
2. **Update Deployment**: Change the image tag in your `docker-compose.yml` or K8s manifest.
3. **Redeploy**:
   ```bash
   docker-compose up -d
   ```
4. **Verify**: Check logs to ensure the old version is running and stable.

### 2.2 Manual/Bare-Metal Deployment
1. **Stop Current Version**: `pkill -f main.py`
2. **Revert Code**: `git checkout stable-tag` or revert to the previous directory.
3. **Check Dependencies**: Ensure no new dependencies from the failed version are causing conflicts.
4. **Restart**: `python main.py --mode demo ...`

### 2.3 Database Migrations Rollback
If the deployment included a database migration:
1. **Check Reversibility**: Use Alembic to downgrade.
   ```bash
   alembic downgrade -1
   ```
2. **Note**: If data was corrupted by the new version, refer to **Runbook 04: Database Corruption**.

## 3. Post-Rollback
1. **Audit Open Positions**: Manually verify that the rolled-back bot correctly identifies all open positions on the MT5 terminal.
2. **Root Cause Analysis (RCA)**: Perform an RCA before attempting another deployment.

## 4. Escalation Path
- **P1 (Failed Deployment)**: Requires immediate rollback. Notify the CTO/Engineering Lead.

## 5. Verification Commands
```bash
# Check running image version
docker ps --format "{{.Image}}"

# Check bot version/logs
grep "Configuration loaded" logs/trading_bot.log | tail -n 1
```

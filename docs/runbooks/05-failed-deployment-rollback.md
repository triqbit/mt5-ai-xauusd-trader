# Runbook 05: Failed Deployment Rollback

## Overview
This runbook details how to roll back a production release that exhibits critical failures immediately after deployment.

## Rollback Triggers
- Error rate > 1% in the first 30 minutes.
- P95 latency increases > 2x baseline.
- High-severity Telegram alerts triggered.
- System fails health/readiness probes.

## Rollback Procedures

### 1. Kubernetes / Containerized Environments
If using the strategies outlined in `DEPLOYMENT_GUIDE.md`:

**Automatic Rollback:**
- Kubernetes will automatically rollback if the `readinessProbe` fails during a `RollingUpdate`.

**Manual Rollback:**
1.  Check rollout history:
    ```bash
    kubectl rollout history deployment/trading-bot
    ```
2.  Undo the last rollout:
    ```bash
    kubectl rollout undo deployment/trading-bot
    ```
3.  Monitor status:
    ```bash
    kubectl rollout status deployment/trading-bot
    ```

### 2. Manual / Docker-Compose Environments
1.  Stop the current container:
    ```bash
    docker-compose down
    ```
2.  Revert the Docker image tag in `docker-compose.yml` to the previous stable version (e.g., from `v1.2.0` to `v1.1.0`).
3.  Start the previous version:
    ```bash
    docker-compose up -d
    ```

### 3. Database Migration Rollback
If the deployment included database schema changes that are incompatible with the previous code version:
1.  Identify the previous migration revision:
    ```bash
    alembic history
    ```
2.  Downgrade the database:
    ```bash
    alembic downgrade <previous-revision-id>
    ```

## Post-Rollback Verification
1.  Check logs for successful startup and connection to MT5.
2.  Verify that error rates have returned to baseline levels.
3.  Send a Telegram notification: `INFO: Deployment rolled back to version XXX. Investigating root cause.`

## Escalation Path
1.  **Level 1:** Release Lead (@andonly1348) for the rollback decision.
2.  **Level 2:** DevOps/Infrastructure for environment stability checks.
3.  **Level 3:** Full Team for "War Room" diagnosis of the failed release.

## Post-Mortem Requirement
A failed deployment requiring rollback MUST be followed by a blameless post-mortem within 48 hours to prevent recurrence.

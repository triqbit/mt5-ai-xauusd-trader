# Runbook 05: Failed Deployment Rollback

## Description
This runbook provides instructions for rolling back a bad release in production.

## Rollback Procedures

### 1. Kubernetes Rollback (Automated)
**Symptom:** New deployment shows high error rate, crashing pods, or failed health checks.
**Step-by-step Instructions:**
1. Check rollout history:
   ```bash
   kubectl rollout history deployment/trading-bot
   ```
2. Undo the rollout to the previous revision:
   ```bash
   kubectl rollout undo deployment/trading-bot
   ```
3. Monitor status:
   ```bash
   kubectl rollout status deployment/trading-bot
   ```

**Expected Outcome:** Deployment reverts to the previous known-good Docker image.

### 2. Manual Version Revert (Git/CI)
**Symptom:** Issue discovered after rollout completion.
**Step-by-step Instructions:**
1. Identify the last stable commit SHA or Tag (e.g., `v1.1.0`).
2. Revert the changes in the main branch or point the `production` branch back to the stable commit.
3. Push changes to trigger CI/CD pipeline.
   ```bash
   git checkout main
   git revert <bad_commit_sha>
   git push origin main
   ```

**Expected Outcome:** CI/CD builds and deploys the stable version.

### 3. Database Migration Rollback (If applicable)
**Symptom:** Rollback of code fails because database schema is incompatible.
**Step-by-step Instructions:**
1. Identify the target migration version (revision).
2. Run Alembic downgrade:
   ```bash
   alembic downgrade -1  # Downgrade by one version
   # OR
   alembic downgrade <revision_id>
   ```

**Expected Outcome:** Database schema is reverted to the previous version.

## Post-Rollback Actions
1. Verify system health and trade execution.
2. Communicate the incident and rollback status to stakeholders.
3. Perform a Post-Mortem to identify root cause.

## Escalation Path
1. Rollback fails: Escalate to SRE / DevOps Lead.
2. Data corruption during migration rollback: Escalate to DBA.

## Verification Commands
```bash
# Check running image version
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# Check Alembic version
alembic current
```

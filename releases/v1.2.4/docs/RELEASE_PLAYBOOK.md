# Release Playbook

This playbook provides a step-by-step guide for operators to execute a production release and handle emergency rollbacks.

## 1. Release Request
1. Ensure all features for the release are merged into the `main` branch.
2. Verify that the version in `pyproject.toml` is correctly incremented following Semantic Versioning.
3. Update `CHANGELOG.md` with the new version details.

## 2. Execution (Automated)
1. Trigger the "Release Orchestration" workflow in GitHub Actions.
2. Provide the version tag (e.g., `v1.1.0`) if prompted.
3. The workflow will:
   - Run the full test suite and security scans.
   - Build and scan the Docker image.
   - Package release artifacts (checksummed).
   - Create a GitHub Release.

## 3. Manual Verification (Post-Deployment)
1. **Health Check**: Access the `/health` endpoint or check the logs for "Bot started successfully".
2. **Connectivity**: Verify the bot has successfully connected to the MT5 server.
3. **Metrics**: Confirm that Prometheus is receiving metrics and the dashboard is updating.
4. **Logs**: Monitor logs for the first 30 minutes for any `CRITICAL` or `ERROR` messages.

## 4. Emergency Rollback
If the deployment causes critical failures or unexpected trading behavior:

### Option A: Automated Rollback (Kubernetes)
If using K8s, execute:
```bash
kubectl rollout undo deployment/mt5-trader
```

### Option B: Manual Tag Revert
1. Identify the last known stable version (e.g., `v1.0.5`).
2. Re-trigger the Release workflow using the stable version tag.
3. Deploy the resulting stable Docker image to production.

### Option C: Circuit Breaker
If the bot is misbehaving but not crashing, trigger the global halt via the risk manager or by setting:
```env
MODE=demo
```
This will prevent any new live trades from being placed while you investigate.

## 5. Escalation Path
- **P1 (System Down / Trading Error)**: Notify Lead Developer and Risk Manager immediately.
- **P2 (Latency / Non-critical Bug)**: Log an issue in GitHub and address in the next patch.

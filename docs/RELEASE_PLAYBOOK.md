# Release Playbook

This document outlines the standard operating procedure (SOP) for releasing new versions of the MT5 AI/ML Trading Bot.

## 1. Release Process Overview

The release process is fully automated via GitHub Actions. It includes:
- Code Quality & Security Validation
- Full Test Suite Execution
- License Compliance Audit
- Docker Image Building & Scanning
- Changelog Generation
- Artifact Packaging
- GitHub Release Creation

## 2. Triggering a Release

### Method A: Manual (Recommended for Production)
1. Go to the **Actions** tab in GitHub.
2. Select the **Release Orchestration** workflow.
3. Click **Run workflow**.
4. Enter the version number (e.g., `1.2.3`).
5. Choose whether to perform a **dry_run** (validation only, no tag/release created).

### Method B: Git Tag
1. Create a semantic version tag locally: `git tag -a v1.2.3 -m "Release v1.2.3"`
2. Push the tag: `git push origin v1.2.3`
3. The workflow will trigger automatically.

## 3. Pre-Production Acceptance
Before triggering a production release, ensure the following:
- [ ] `docs/PREPROD_CHECKLIST.md` is updated and reviewed.
- [ ] Backtest results for the new version meet the internal benchmarks.
- [ ] No critical security vulnerabilities are reported by the CI pipeline.

## 4. Verification After Release
1. Check the **Releases** page on GitHub.
2. Verify that the ZIP artifact and `checksums.txt` are present.
3. Verify that the `CHANGELOG.md` accurately reflects the changes.
4. (Optional) Download the artifact and verify the checksum:
   ```bash
   sha256sum -c checksums.txt
   ```

## 5. Rollback Procedures

### Container Rollback
If the new Docker image is unstable, revert to the previous version immediately:
```bash
# 1. Update the image tag in your deployment manifest or docker-compose.yml
# From: triqbit/mt5-ai-xauusd-trader:v1.2.3
# To:   triqbit/mt5-ai-xauusd-trader:v1.2.2

# 2. Pull the stable image
docker pull triqbit/mt5-ai-xauusd-trader:v1.2.2

# 3. Restart the service
docker-compose up -d trading-bot
```

### Database Migration Rollback
If a schema change causes issues, downgrade the database:
```bash
# 1. Enter the running container (or local environment)
# 2. Run the alembic downgrade command (one step back)
alembic downgrade -1

# 3. Verify current version
alembic current
```

### Emergency "Kill Switch"
In case of catastrophic trading behavior:
1. Log in to the MT5 Terminal or VPS.
2. Manually close all open XAUUSD positions.
3. Stop the Docker container: `docker stop trading-bot`.

## 6. Post-Release Verification Checklist
After a successful deployment, the operator MUST verify the following:
- [ ] **Liveness:** `curl http://localhost:8000/health/liveness` returns `{"status": "ok"}`.
- [ ] **MT5 Connection:** Logs show "Successfully connected to MT5 account XXXXXX".
- [ ] **Audit Trail:** Check `trades.db` for the initial "System Startup" audit entry.
- [ ] **Telegram:** Confirm the "Trading Bot Started (vX.Y.Z)" message was received.

## 7. Incident Response
- **Workflow Failure:** Check the GitHub Actions logs for the specific job that failed. Common issues include dependency conflicts, test failures, or expired secrets.
- **Security Alert:** If Trivy or pip-audit fails, do not bypass. Fix the vulnerabilities before proceeding.
- **Connectivity Issues:** Ensure the GitHub runner has access to required external resources (e.g., Docker Hub, if pushing).

---
**Author:** Jules03 (Release Reliability & Governance)
**Last Updated:** May 2024

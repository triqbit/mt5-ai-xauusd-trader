# Release Playbook

This document outlines the standard operating procedure (SOP) for releasing new versions of the MT5 AI/ML Trading Bot.

## 1. Release Process Overview

The release process is fully automated via GitHub Actions. It includes:
- **Validation Stage:** Code quality (Ruff), static analysis (Mypy), security audit (pip-audit), license compliance (pip-licenses), and full test suite execution with 85% coverage enforcement. It also includes an **Automated Pre-Prod Checklist Verification** to ensure all mandatory gates are completed.
- **Build Stage:** Docker image building and automated vulnerability scanning (Trivy).
- **Release Stage:** Automated version bumping, changelog transition, Git tagging, artifact packaging (including integrity checksums), and GitHub Release creation.

## 2. Triggering a Release

### Method A: Manual (Recommended for Production)
1. Go to the **Actions** tab in GitHub.
2. Select the **Release Orchestration** workflow.
3. Click **Run workflow**.
4. Enter the version number (e.g., `1.2.3`). Leave empty to auto-calculate.
5. Choose whether to perform a **dry_run** (validation only, no tag/release created).

### Method B: Git Tag
1. Create a semantic version tag locally: `git tag -a v1.2.3 -m "Release v1.2.3"`
2. Push the tag: `git push origin v1.2.3`
3. The workflow will trigger automatically.

## 3. Pre-Production Acceptance
Before triggering a production release, the operator MUST ensure that `docs/PREPROD_CHECKLIST.md` is updated and all mandatory items are checked `[x]`.
The CI workflow will automatically verify that no incomplete items `[ ]` remain in the checklist.

## 4. Verification After Release
1. Check the **Releases** page on GitHub.
2. Verify that the ZIP artifact and `checksums.txt` are present.
3. Verify that the `CHANGELOG.md` accurately reflects the changes.
4. Download the artifact and verify the checksum:
   ```bash
   sha256sum -c checksums.txt
   ```

## 5. Rollback Procedures

Rollback decisions are governed by the Stability Freeze protocol in [SLO Targets](SLO_TARGETS.md).

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
In case of catastrophic trading behavior or risk limit breach:
1. **Halt Execution:** Log in to the MT5 Terminal or VPS.
2. **Close Exposure:** Manually close all open XAUUSD positions.
3. **Terminate Process:** Stop the Docker container: `docker stop trading-bot`.
4. **Audit Log:** Document the event in the Audit Log using `scripts/data_cleanup.py` if necessary for archival.

## 6. Disaster Recovery Integration

In the event of database corruption during or after release:
1. **Locate Backup:** Find the latest hourly backup in `/backups/trades.db.bak`.
2. **Verify Integrity:** Run `scripts/backup_verify.sh` to ensure the backup is valid.
3. **Restore:** Follow the recovery steps in [Disaster Recovery](DISASTER_RECOVERY.md).

## 7. Post-Release Verification Checklist
After a successful deployment, the operator MUST verify the following:
- [ ] **Liveness:** `curl http://localhost:8000/health/liveness` returns `{"status": "ok"}`.
- [ ] **MT5 Connection:** Logs show "Successfully connected to MT5 account XXXXXX".
- [ ] **Audit Trail:** Check `trades.db` for the initial "System Startup" audit entry.
- [ ] **Telegram:** Confirm the "Trading Bot Started (vX.Y.Z)" message was received.

## 8. Incident Response
- **Workflow Failure:** Check the GitHub Actions logs for the specific job that failed. Common issues include dependency conflicts, test failures, or expired secrets.
- **Security Alert:** If Trivy or pip-audit fails, do not bypass. Fix the vulnerabilities before proceeding.
- **Connectivity Issues:** Ensure the GitHub runner has access to required external resources (e.g., Docker Hub, if pushing).

---
**Author:** Jules03 (Release Reliability & Governance)
**Last Updated:** May 2024

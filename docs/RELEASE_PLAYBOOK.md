# Release Playbook

This document defines the standard operating procedure (SOP) for releasing new versions of the MT5 AI/ML Trading Bot. It ensures that every release is predictable, audited, and recoverable.

## 1. Release Process Overview

The release process is fully automated via GitHub Actions (`.github/workflows/release.yml`). The workflow enforces a "Chain of Trust" through three distinct stages:

1.  **Validation Stage:**
    - Code quality and formatting (Ruff).
    - Static type analysis (Mypy).
    - Secret scanning (Gitleaks).
    - Dependency security audits (`pip-audit`).
    - License compliance verification (`pip-licenses`).
    - Full test suite execution with a mandatory **85% code coverage gate**.
    - Configuration and environment template validation (`scripts/validate_env.py`).
    - Database migration reversibility checks (`scripts/verify_migrations.py`).
    - **Automated Pre-Prod Checklist Verification**: Ensures `docs/PREPROD_CHECKLIST.md` contains no unchecked items `[ ]`.

2.  **Build Stage:**
    - Multi-stage Docker image build.
    - Automated vulnerability scanning using Trivy (failing on CRITICAL or HIGH vulnerabilities).

3.  **Release Stage:**
    - Automated version bumping and `CHANGELOG.md` finalization.
    - Git tagging.
    - Artifact packaging with SHA256 integrity checksums.
    - Creation of a GitHub Release with version-specific notes and rollback links.

---

## 2. Triggering a Release

### Method A: Manual Trigger (Recommended)
1.  Navigate to the **Actions** tab in the GitHub repository.
2.  Select the **Release Orchestration** workflow (`release.yml`).
3.  Click **Run workflow** dropdown on the right side.
4.  Select the **Branch** (usually `main`).
5.  Fill in the parameters:
    - **Version**: Enter the target semantic version (e.g., `1.2.3`).
        - *Note*: If left empty, the system will use `mathieudutour/github-tag-action` to calculate the next version based on [Conventional Commits](VERSIONING_POLICY.md).
    - **Prerelease**: Toggle this if creating a Release Candidate (`-rc.N`) or beta build.
    - **Dry Run**: Toggle this to execute all validation, test, and build steps *without* creating a Git tag, pushing code changes, or publishing a GitHub Release. Use this for final verification before a real push.
6.  Click **Run workflow** button to start the process.

### Method B: Git Tag Push
1.  Tag the desired commit locally: `git tag -a v1.2.3 -m "Release v1.2.3"`
2.  Push the tag: `git push origin v1.2.3`
3.  The workflow will detect the tag and proceed directly to validation and release (skipping code-level version bumping).

---

## 3. Pre-Production Acceptance Gate

Before any production release, the operator **MUST** update `docs/PREPROD_CHECKLIST.md`.
- All mandatory items must be checked `[x]`.
- The CI workflow will automatically fail if any `[ ]` markers are found.
- Ensure backtest results are attached to the release or linked in the changelog.

---

## 4. Post-Release Verification Checklist

Immediately following a deployment, the operator MUST perform the following checks:

- [ ] **Liveness Probe:** `curl http://<deploy-host>:8000/health/liveness` returns `{"status": "ok"}`.
- [ ] **MT5 Connectivity:** Check logs for "Successfully connected to MT5 account: <ID>".
- [ ] **Audit Trail:** Verify a "System Startup" event is recorded in the `audit_log` table of `audit.db`.
- [ ] **Telegram Alerts:** Confirm receipt of the "Trading Bot Started (vX.Y.Z)" notification.
- [ ] **Metric Flow:** Verify that Prometheus metrics are being populated at `/metrics`.

---

## 5. Rollback Procedures

Rollback decisions are governed by the Stability Freeze protocol defined in [SLO Targets](SLO_TARGETS.md).

### A. Container Image Rollback
If the new version exhibits unstable behavior (high latency, frequent crashes, memory leaks):
1.  **Identify Stable Version**: Find the last known stable tag from the [Releases](https://github.com/triqbit/mt5-ai-xauusd-trader/releases) page (e.g., `v1.2.2`).
2.  **Update Manifest**: Modify your `docker-compose.yml` or K8s deployment to point to the stable image:
    ```yaml
    image: triqbit/mt5-ai-xauusd-trader:v1.2.2
    ```
3.  **Redeploy**: Restart the service:
    ```bash
    docker-compose up -d --force-recreate
    ```
4.  **Verify**: Check health status immediately: `curl http://localhost:8000/health/readiness`.

### B. Code/Git Rollback
If the release contains functional bugs or logic errors that require a full revert:
1.  **Revert Tag**: If the tag was created erroneously, delete it (carefully):
    ```bash
    git tag -d v1.2.3
    git push --delete origin v1.2.3
    ```
2.  **Revert Commits**: Use `git revert` on the merge commit or release commit to return `main` to the previous state.
3.  **Update Version**: Ensure `pyproject.toml` version is corrected if a bump occurred.

### C. Database Migration Rollback
If a schema change causes data corruption or application failure:
1.  Exec into the running container: `docker exec -it trading-bot bash`.
2.  Downgrade the schema by one version: `alembic downgrade -1`.
3.  Verify the current version: `alembic current`.

### C. MT5 Emergency Kill-Switch
In case of catastrophic trading behavior (e.g., rogue orders, risk limit bypass):
1.  **Immediate Halt:** Stop the Docker container: `docker stop trading-bot`.
2.  **Physical Disconnect:** If possible, disconnect the internet connection of the host/VPS.
3.  **Terminal Force Quit:**
    - Linux (Wine): `pkill -9 terminal.exe`
    - Windows: Task Manager -> End Task on `terminal.exe`.
4.  **Credential Invalidation:** Log in to your broker's portal and **change the MT5 account password** immediately. This will force-disconnect any active sessions.
5.  **Manual Cleanup:** Log in to the MT5 mobile app or another terminal to manually close all open positions.

---

## 6. Disaster Recovery Integration

If the deployment causes unrecoverable database state:
1.  Follow the [Disaster Recovery Plan](DISASTER_RECOVERY.md).
2.  Restore the latest hourly backup from `backups/trades.db.bak` using `scripts/backup_verify.sh`.
3.  Re-verify the restored data against the `AuditLogger` records.

---
**Author:** Jules03 (Release Reliability & Governance)
**Last Updated:** 2024-05-24

# 📖 Release Playbook: MT5 AI/ML Trading Bot

This playbook provides step-by-step instructions for the Release Engineer (Jules03) to orchestrate a production release.

---

## 1. 🚦 Release Workflow Overview

The release process is fully automated via GitHub Actions, but requires manual initiation and validation of the Pre-Production Gate.

**Trigger:**
- Manual trigger via **GitHub Actions Tab** -> **Release Pipeline**.
- Automatic trigger when a tag matching `v*` is pushed.

---

## 2. 🛠️ Execution Steps

### Step 1: Pre-Release Validation (Local/Staging)
Before triggering the workflow, ensure the local environment is clean:
```bash
# Run full test suite
python -m pytest tests/ --cov=src

# Verify license compliance
pip-licenses --allow-only "MIT;Apache 2.0;BSD;PSF-2.0;ISC;Unlicense;CC0"
```

### Step 2: Bump Version
Update the version strings in:
1. `src/__init__.py`: `__version__ = "X.Y.Z"`
2. `pyproject.toml`: `version = "X.Y.Z"`

Commit and push to `develop` then merge to `main`.

### Step 3: Trigger the Workflow
1. Navigate to the **Actions** tab in GitHub.
2. Select the **Release Pipeline** workflow.
3. Click **Run workflow** (select the `main` branch).
4. Provide the version number when prompted (e.g., `1.0.1`).

### Step 4: Manual Sign-off
After the `package` job completes, the workflow will pause for manual approval.
1. Review the **Checks** or **Environments** tab in the GitHub UI.
2. Verify that all automated tests and security scans passed.
3. If valid, click **Approve and Deploy** for the `production` environment.

### Step 5: Verification
The workflow will:
1. Run `quality`, `security`, and `test` jobs.
2. Build and scan the Docker image (Trivy).
3. Validate the `PREPROD_CHECKLIST.md` (manual gate).
4. Package release artifacts and generate checksums.
5. Create a GitHub Release with auto-generated notes from PR history.

---

## 3. 🔄 Rollback Procedures

If the release fails health checks in production, follow these steps immediately.

### Scenario A: Deployment Failure (K8s/Docker)
If the new container fails to start or pass readiness probes:
```bash
# Automated rollback to previous stable version
kubectl rollout undo deployment/trading-bot

# Verify status
kubectl rollout status deployment/trading-bot
```

### Scenario B: Database Migration Issue
If a migration causes data inconsistency:
```bash
# Revert the last migration
alembic downgrade -1

# Verify database integrity
sqlite3 trades.db "PRAGMA integrity_check;"
```

### Scenario C: Critical Logic Error
If the bot exhibits dangerous trading behavior:
1. **Emergency Stop:** `python main.py --halt "Emergency: Release vX.Y.Z instability"`
2. **Revert Git:** Revert the merge to `main` and redeploy the previous tag.

---

## 📋 Release Sign-off Reference

| Phase | Responsibility | Tool |
| :--- | :--- | :--- |
| **Lint/Quality** | CI | Ruff, Mypy |
| **Security** | CI | pip-audit, Trivy |
| **Testing** | CI | Pytest (>80% cov) |
| **Packaging** | CI | package_release.sh |
| **Sign-off** | Jules03 | PREPROD_CHECKLIST.md |

---
**Last Updated:** 2026-04-28 by Jules03

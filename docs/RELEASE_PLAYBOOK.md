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
    - **Atlas Governance Audit (Gate 4.8)**: Verifies synchronization between `RISK_LIMITS.md` and `src/core/config.py`, and ensures runbook integrity.
    - Configuration and environment template validation (`scripts/validate_env.py`).
    - Database migration reversibility checks (`scripts/verify_migrations.py`).
    - **Automated Pre-Prod Checklist Verification**: Ensures `docs/PREPROD_CHECKLIST.md` contains no unchecked items `[ ]`.

2.  **Research & QA Stage (Jules02 Integration):**
    - Institutional Walk-Forward Optimization Verification.
    - StressLab resilience testing against extreme volatility.
    - Rare-event simulation (Flash Crash/Liquidity Vacuum).
    - Benchmarking against technical and random baselines.
    - **Capital Allocation Reporting** verification.
    - **Backtest Audit Traceability** verification.
    - **Journal Mining & Pattern Detection** verification.
    - **Model Explainability & UI** verification.
    - **UX Terminal & Decision Support** verification.
    - **Consolidated Research Audit Report** generation (`research_audit_report.md`).
    - **Reliability SLO Audit**: Verification of uptime, RTO, and error budget targets.

3.  **Build & Runtime Verification Stage:**
    - Multi-stage Docker image build.
    - Automated vulnerability scanning using Trivy (failing on CRITICAL or HIGH vulnerabilities).
    - **Automated Runtime Smoke Test**: Spins up the freshly built container and verifies API liveness/readiness via `scripts/smoke_test.py`.

4.  **Release Stage:**
    - Automated version bumping and `CHANGELOG.md` finalization.
    - Git tagging.
    - Artifact packaging with SHA256 integrity checksums via `scripts/package_release.sh`.
    - Creation of a GitHub Release with version-specific notes, integrity verification, and quick-rollback links.

---

## 2. Triggering a Release

### Method A: Manual Trigger (Recommended)
1.  Navigate to the **Actions** tab in the GitHub repository.
2.  Select the **Release Orchestration** workflow (`release.yml`).
3.  Click **Run workflow** dropdown on the right side.
4.  Select the **Branch** (usually `main`).
5.  Fill in the parameters:
    - **Version**: Enter the target semantic version (e.g., `1.2.3`).
        - *Note*: If left empty, the system will calculate the next version based on [Conventional Commits](VERSIONING_POLICY.md).
    - **Prerelease**: Toggle this if creating a Release Candidate (`-rc.N`) or beta build.
    - **Dry Run**: Toggle this to execute all validation, test, and build steps *without* creating a Git tag, pushing code changes, or publishing a GitHub Release. Use this for final verification before a real push.
6.  Click **Run workflow** button to start the process.

### Method B: Git Tag Push
1.  Tag the desired commit locally: `git tag -a v1.2.3 -m "Release v1.2.3"`
2.  Push the tag: `git push origin v1.2.3`
3.  The workflow will detect the tag and proceed directly to validation and release (skipping code-level version bumping).

---

## 3. Governance & Multi-Signature Approval

As defined in [CONTRIBUTING.md](CONTRIBUTING.md), any release affecting **Sensitive Zones** (Trading, Models, Core) requires mandatory multi-signature approval.

- **Domain Lead Approval**: Review by the lead of the affected module (e.g., `@maintainer-trading`).
- **Governance Sign-off**: Final approval and sign-off by the Release/Governance lead (@andonly1348).
- **QA Verification**: Confirmation from the Quality Lead (@maintainer-quality) that all Research Vitals and test gates have passed.

## 4. Pre-Production Acceptance Gate

Before any production release, the operator **MUST** update `docs/PREPROD_CHECKLIST.md`.
- All mandatory items must be checked `[x]`.
- The CI workflow will automatically fail if any `[ ]` markers are found.
- Ensure backtest and Research Vitals reports are attached to the release or linked in the changelog.

---

## 5. Post-Release Verification Checklist

Immediately following a deployment, the operator MUST perform the following checks:

- [ ] **Liveness Probe:** `curl http://<deploy-host>:8000/health/liveness` returns `{"status": "ok"}`.
- [ ] **MT5 Connectivity:** Check logs for "Successfully connected to MT5 account: <ID>".
- [ ] **Audit Trail:** Verify a "System Startup" event is recorded in the `audit_log` table of `audit.db`.
- [ ] **Telegram Alerts:** Confirm receipt of the "Trading Bot Started (vX.Y.Z)" notification.
- [ ] **Metric Flow:** Verify that Prometheus metrics are being populated at `/metrics`.

---

## 6. Rollback Procedures

Rollback decisions are governed by the Stability Freeze protocol defined in [SLO Targets](SLO_TARGETS.md).

### A. Container Image Rollback (Fastest)
If the new version exhibits unstable behavior (high latency, frequent crashes, memory leaks):
1.  **Identify Stable Version**: Find the last known stable tag from the [Releases](https://github.com/triqbit/mt5-ai-xauusd-trader/releases) page (e.g., `v1.2.2`).
2.  **Redeploy**: Run the following command on the production host:
    ```bash
    # 1. Stop the current unstable container
    docker stop trading-bot

    # 2. Start the previous stable version (e.g., v1.2.2)
    export STABLE_TAG=v1.2.2
    docker run -d \
      --name trading-bot \
      --restart always \
      --env-file .env \
      -p 8000:8000 \
      -v $(pwd)/data:/app/data \
      triqbit/mt5-ai-xauusd-trader:${STABLE_TAG}
    ```
3.  **Verify**: Check health status immediately:
    ```bash
    # Verify liveness
    curl -f http://localhost:8000/health/liveness
    # Verify readiness (wait up to 30s)
    for i in {1..6}; do curl -s http://localhost:8000/health/readiness | grep -q "UP" && break || sleep 5; done
    ```

### B. Code/Git Rollback
If the release contains functional bugs or logic errors that require a full revert:
1.  **Revert Tag**: If the tag was created erroneously, delete it:
    ```bash
    git tag -d v1.2.3
    git push --delete origin v1.2.3
    ```
2.  **Revert Commits**: Use `git revert` on the merge commit or release commit to return `main` to the previous state.
3.  **Update Version**: Ensure `pyproject.toml` version is corrected if a bump occurred.

### C. Database Migration Rollback
If a schema change causes data corruption or application failure:
1.  **Exec into the running container**:
    ```bash
    docker exec -it trading-bot bash
    ```
2.  **Downgrade the schema**:
    ```bash
    # Downgrade by one version
    alembic downgrade -1
    ```
3.  **Verify current schema version**:
    ```bash
    alembic current
    ```
4.  **Restart the container** (to ensure application state is synchronized with DB):
    ```bash
    exit
    docker restart trading-bot
    ```

### D. Emergency Protocols & MT5 Kill-Switch
In case of catastrophic trading behavior, risk limit breaches, or circuit breaker activation (e.g., rogue orders, risk limit bypass):
1.  **Immediate Halt:** Stop the Docker container: `docker stop trading-bot`.
2.  **Physical Disconnect:** If possible, disconnect the internet connection of the host/VPS.
3.  **Terminal Force Quit:**
    - Linux (Wine): `pkill -9 terminal.exe`
    - Windows: Task Manager -> End Task on `terminal.exe`.
4.  **Credential Invalidation:** Log in to your broker's portal and **change the MT5 account password** immediately. This will force-disconnect any active sessions.
5.  **Manual Cleanup:** Log in to the MT5 mobile app or another terminal to manually close all open positions.

---

## 7. Troubleshooting Release Failures

- **Validation Gate Failure**: Check CI logs for the specific gate (e.g., Ruff, Mypy, Pytest). Fix the issues in the source branch and re-run.
- **Atlas Audit Failure**: Verify synchronization between `RISK_LIMITS.md` and `src/core/config.py`.
- **Trivy Security Failure**: Update the base image or vulnerable library in `requirements.txt`.
- **Smoke Test Failure**: Review container logs using `docker logs <container_id>`. Common issues include missing environment variables or database connection timeouts.
- **Checksum Mismatch**: Ensure no manual changes were made to the `releases/vX.Y.Z/` directory after `package_release.sh` finished.

---

## 8. Disaster Recovery Integration

If the deployment causes unrecoverable database state:
1.  Follow the [Disaster Recovery Plan](DISASTER_RECOVERY.md).
2.  Restore the latest hourly backup from `backups/trades.db.bak` using `scripts/backup_verify.sh`.
3.  Re-verify the restored data against the `AuditLogger` records.

---
**Author:** Jules03 (Release Reliability & Governance)
**Last Updated:** 2024-06-15

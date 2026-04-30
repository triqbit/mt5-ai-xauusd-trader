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

### Automated Rollback (Redeploy Previous Version)
If a new release causes issues in production:
1. Identify the last known stable version (e.g., `v1.2.2`).
2. Re-run the **Release Orchestration** workflow with the stable version number (if applicable) or manually trigger the deployment of the stable Docker image.
3. If using Docker, update the production environment to point to the previous stable image tag.

### Manual Rollback (Git)
1. Revert the problematic commits on the `main` branch.
2. Create a new "fix" release (e.g., `v1.2.4`) following the standard process.

## 6. Incident Response
- **Workflow Failure:** Check the GitHub Actions logs for the specific job that failed. Common issues include dependency conflicts, test failures, or expired secrets.
- **Security Alert:** If Trivy or pip-audit fails, do not bypass. Fix the vulnerabilities before proceeding.
- **Connectivity Issues:** Ensure the GitHub runner has access to required external resources (e.g., Docker Hub, if pushing).

---
**Author:** Jules03 (Release Reliability & Governance)
**Last Updated:** May 2024

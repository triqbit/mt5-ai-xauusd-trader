# Runbook 01: CI Failure Recovery

## Overview
This runbook provides procedures for recovering from failures in GitHub Actions workflows, including `ci.yml`, `release.yml`, and `pre-deploy-validation.yml`.

## Common Failures & Resolutions

### 1. Linting Failures (Ruff)
**Symptom:** The `lint` job fails with code style or import errors.
**Resolution:**
1. Run Ruff locally to identify and fix issues:
   ```bash
   ruff check . --fix
   ruff format .
   ```
2. Ensure imports are sorted (I001):
   ```bash
   ruff check . --select I --fix
   ```
3. Commit and push the fixes.

### 2. Test Failures (Pytest)
**Symptom:** The `test` job fails due to failed assertions or errors.
**Resolution:**
1. Run tests locally:
   ```bash
   python -m pytest tests/
   ```
2. If coverage is below 80%, identify uncovered areas:
   ```bash
   python -m pytest --cov=src tests/ --cov-report=term-missing
   ```
3. Fix the failing tests or add missing coverage.
4. Ensure no regression in `Migration Reversibility Check`.

### 3. Security Scan Failures (Trivy / pip-audit)
**Symptom:** `security-scan` or `dependency-audit` fails.
**Resolution:**
1. **Dependency Vulnerability:**
   - Update the vulnerable package in `requirements.txt`.
   - Run `pip-audit` locally to verify.
2. **Secret Detection:**
   - If Gitleaks/Trivy detects a secret, **revoke the secret immediately**.
   - Remove the secret from Git history (e.g., using BFG Repo-Cleaner or `git filter-repo`).
   - Rotate the secret.
3. **Docker Image Vulnerabilities:**
   - Update the base image in `Dockerfile`.
   - Re-run the scan.

### 4. Versioning / Release Failures
**Symptom:** `release` workflow fails during version bumping or changelog generation.
**Resolution:**
1. Ensure `pyproject.toml` and `src/__init__.py` versions match.
2. Check if `CHANGELOG.md` has an `[Unreleased]` section.
3. Verify that the commit message follows Conventional Commits.

## Verification
- Monitor the GitHub Actions tab for the specific PR or branch.
- Ensure all status checks are green before merging.

## Escalation Path
1. **Level 1:** DevOps / Release Engineer (Jules03).
2. **Level 2:** Core Maintainers.
3. **Level 3:** Security Lead (if security-related).

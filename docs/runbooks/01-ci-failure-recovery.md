# Runbook 01: CI Failure Recovery

## Overview
This runbook provides procedures for recovering from failures in GitHub Actions workflows, including `ci.yml`, `release.yml`, and `pre-deploy-validation.yml`. These gates are mandatory for production releases.

## Common Failures & Resolutions

### 1. Linting & Type Check Failures (Ruff / Mypy)
**Symptom:** The `lint` or `type-check` job fails.
**Resolution:**
1. Run Ruff locally to identify and fix issues:
   ```bash
   ruff check . --fix
   ruff format .
   ```
2. Run Mypy to check for type inconsistencies:
   ```bash
   mypy src/ main.py
   ```
3. Commit and push the fixes.

### 2. Test & Coverage Failures (Pytest)
**Symptom:** The `test` job fails due to failed assertions or coverage falling below the 85% gate.
**Resolution:**
1. Run tests locally:
   ```bash
   python -m pytest tests/
   ```
2. If coverage is below 85%, identify uncovered areas:
   ```bash
   python -m pytest --cov=src tests/ --cov-report=term-missing
   ```
3. Ensure no regression in `Migration Reversibility Check`.

### 3. Security Scan Failures (Trivy / pip-audit / Gitleaks)
**Symptom:** `security-scan` or `dependency-audit` fails.
**Resolution:**
1. **Dependency Vulnerability (pip-audit):**
   - Run `pip-audit` locally.
   - Update the vulnerable package in `requirements.txt`.
2. **Secret Detection (Gitleaks):**
   - If a secret is detected, **revoke the secret immediately**.
   - Remove the secret from Git history using `git filter-repo`.
   - Rotate the secret across all environments.
3. **Docker Image Vulnerabilities (Trivy):**
   - Update the base image in `Dockerfile` or fix vulnerable OS packages.

### 4. Validation Script Failures
**Symptom:** Failures in `validate_env.py` or `verify_migrations.py`.
**Resolution:**
1. **Environment Validation (`validate_env.py`):**
   - Check if `.env.example` is missing keys defined in `src/core/config.py`.
   - Run: `python scripts/validate_env.py`
2. **Migration Safety (`verify_migrations.py`):**
   - Ensure migrations are reversible (upgrade -> downgrade -> upgrade).
   - Check for schema inconsistencies in `migrations/versions/`.
   - Run: `python scripts/verify_migrations.py`

### 5. Release Readiness Failures
**Symptom:** `release` workflow fails during version bumping or changelog checks.
**Resolution:**
1. Ensure `CHANGELOG.md` has a non-empty `## [Unreleased]` section.
2. Run: `python scripts/check_release_notes.py`
3. Verify that the commit message follows Conventional Commits.

## Expected Outcomes
- All GitHub Actions workflows show a green "Success" status.
- The 85% coverage gate is satisfied (aligned with `EXCELLENCE_BLUEPRINT.md`).
- No high-severity vulnerabilities or leaked secrets remain.

## Verification Commands
- **Environment:** `python scripts/validate_env.py`
- **Migrations:** `python scripts/verify_migrations.py`
- **Tests:** `pytest tests/ --cov=src --cov-fail-under=85`
- **Security:** `pip-audit` and `gitleaks detect --verbose`

## Escalation Path
1. **Level 1:** Release Engineer (Jules03).
2. **Level 2:** Quality Lead (@maintainer-quality).
3. **Level 3:** Security Lead (if security-related).

# Runbook 01: CI Failure Recovery

## Overview
This runbook provides standardized procedures for recovering from failures in GitHub Actions workflows, including `ci.yml`, `release.yml`, and `pre-deploy-validation.yml`. These gates are mandatory "Quality Gates" that must pass for any code to reach production.

## Common Failures & Resolutions

### 1. Linting & Type Check Failures (Ruff / Mypy)
**Symptom:** The `lint` or `type-check` job fails in the CI pipeline.
**Resolution:**
1. **Ruff:** Identify linting errors in the CI logs. Run Ruff locally to fix:
   ```bash
   ruff check . --fix
   ruff format .
   ```
2. **Mypy:** Check for type inconsistencies. Run Mypy locally:
   ```bash
   mypy src/ main.py scripts/
   ```
3. Commit and push the fixes once local checks pass.

### 2. Test & Coverage Failures (Pytest)
**Symptom:** The `test` job fails due to failed assertions or coverage falling below the **85%** gate.
**Resolution:**
1. **Identify Failures:** Review the Pytest output in GitHub Actions.
2. **Run Locally:** Execute the test suite locally to reproduce:
   ```bash
   python -m pytest tests/
   ```
3. **Check Coverage:** If coverage is below 85%, generate a report to find uncovered lines:
   ```bash
   python -m pytest --cov=src tests/ --cov-report=term-missing
   ```
4. **Migration Reversibility:** Ensure no regression in the `verify_migrations.py` check.

### 3. Security Scan Failures (Trivy / pip-audit / Gitleaks)
**Symptom:** `security-scan` or `dependency-audit` fails.
**Resolution:**
1. **Dependency Vulnerability (pip-audit):**
   - Run `pip-audit` locally to identify the vulnerable package.
   - Update the package version in `requirements.txt`.
2. **Secret Detection (Gitleaks):**
   - **CRITICAL:** If a secret is detected, it is considered compromised.
   - **Revoke** the secret immediately at the provider (MetaAPI, Telegram, etc.).
   - Use `git filter-repo` or `BFG Repo-Cleaner` to purge the secret from Git history if pushed to a public/shared branch.
   - Rotate the secret across all environments.
3. **Container Security (Trivy):**
   - Check for OS-level vulnerabilities in the base image. Update the `Dockerfile` to a newer base image if necessary.

### 4. Validation Script Failures
**Symptom:** Failures in `validate_env.py` or `verify_migrations.py`.
**Resolution:**
1. **Environment Validation:** Ensure `.env.example` contains all keys required by `Config`. Run:
   ```bash
   python scripts/validate_env.py
   ```
2. **Migration Safety:** Ensure migrations can be upgraded and downgraded cleanly. Run:
   ```bash
   python scripts/verify_migrations.py
   ```

## Expected Outcomes
- GitHub Actions workflows display a green "Success" status.
- All code complies with `EXCELLENCE_BLUEPRINT.md` standards.
- Test coverage meets or exceeds the 85% mandatory threshold.

## Verification Commands
- **Environment:** `python scripts/validate_env.py`
- **Migrations:** `python scripts/verify_migrations.py`
- **Full Test Suite:** `pytest tests/ --cov=src --cov-fail-under=85`
- **Linting:** `ruff check .`
- **Security:** `pip-audit`

## Escalation Path
1. **Level 1:** Release Engineer (Jules03 - @andonly1348).
2. **Level 2:** Quality Lead (@maintainer-quality).
3. **Level 3:** Security Lead (if Gitleaks/Trivy related).

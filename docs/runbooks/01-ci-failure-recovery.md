# Runbook 01: CI Failure Recovery
**Version:** 1.1 | **Last Updated:** 2026-05-07

## Overview
Standardized procedures for recovering from failures in GitHub Actions workflows (CI, Release, Pre-Deployment Validation). These gates are mandatory "Quality Gates".

## Step-by-Step Instructions

### 1. Linting & Type Check Failures
- **Symptoms:** `lint` or `type-check` jobs show red cross in PR.
- **Actions:**
  1. Pull latest changes: `git pull origin <branch>`
  2. Run Ruff: `ruff check . --fix && ruff format .`
  3. Run Mypy: `mypy src/ main.py scripts/`
  4. Fix all reported errors and commit.

### 2. Test & Coverage Failures
- **Symptoms:** `test` job fails; Coverage < 85%.
- **Actions:**
  1. Execute local suite: `python -m pytest tests/`
  2. Identify failing test cases and fix logic.
  3. Check coverage: `python -m pytest --cov=src tests/ --cov-report=term-missing`
  4. Add tests for uncovered lines in `src/`.

### 3. Security Scan Failures
- **Symptoms:** `security-scan` or `dependency-audit` fails.
- **Actions:**
  1. Check `pip-audit` output for vulnerable packages.
  2. Update `requirements.txt` to patched versions.
  3. If Gitleaks fails, **IMMEDIATELY** revoke the leaked secret and rotate it.

## Expected Outcomes
- All GitHub Actions workflows return a "Success" status.
- Code matches the repository's excellence standards.
- Production deployment gates are unlocked.

## Verification Commands
- `python scripts/validate_env.py`
- `python scripts/verify_migrations.py`
- `pytest tests/ --cov=src --cov-fail-under=85`

## Escalation Path
1. **P2/P3 Failures:** Core Maintainer (@maintainer-quality).
2. **P0/P1 Security:** Security Lead (@xnessom).
3. **Blocked Release:** Release Reliability Engineer (Jules03).

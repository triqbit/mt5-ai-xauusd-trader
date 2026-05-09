# Runbook 01: CI Failure Recovery
**Version:** 1.3 | **Last Updated:** 2024-05-22

## Overview
Standardized procedures for recovering from failures in GitHub Actions workflows (CI, Release, Pre-Deployment Validation). These gates are mandatory "Quality Gates" and must pass before any merge to `main`.

## Step-by-Step Instructions

### 1. Automated Triage (Multi-PR Failure)
If multiple PRs are failing or the repository state is turbulent, use the triage report tool:
```bash
export GITHUB_TOKEN="your_token"
python scripts/generate_triage_report.py
```
- Review `docs/status/PR_TRIAGE_DAILY.md` for a high-level view of repository health and risk levels.

### 2. Linting & Type Check Failures
- **Symptoms:** `lint` or `type-check` jobs show red cross in PR.
- **Actions:**
  1. Pull latest changes: `git pull origin <branch>`
  2. Run Ruff: `ruff check . --fix && ruff format .`
  3. Run Mypy: `mypy src/ main.py scripts/`
  4. Fix all reported errors. Common issues include missing type hints or unused imports.
  5. Commit and push fixes.

### 3. Test & Coverage Failures
- **Symptoms:** `test` job fails; Coverage < 85%.
- **Actions:**
  1. Execute local suite: `python -m pytest tests/`
  2. Identify failing test cases by reviewing the CI log output.
  3. Check coverage report: `python -m pytest --cov=src tests/ --cov-report=term-missing`
  4. Identify lines in `src/` that are not covered.
  5. Add unit or integration tests to reach the 85% mandatory threshold.
  6. Ensure `tests/test_governance_vitals.py` passes if any governance files were moved.

### 4. Security Scan Failures
- **Symptoms:** `security-scan`, `gitleaks`, or `trivy` jobs fail.
- **Actions:**
  1. **Gitleaks (Secret Detection):** Review the CI log to see which file triggered the alert. **IMMEDIATELY** revoke the leaked secret at the provider and rotate it. Use `git filter-repo` or similar if the secret must be scrubbed from history.
  2. **Trivy (Container Scan):** Check for vulnerable base images or OS packages. Update the `Dockerfile` to use a later patched version of the base image.
  3. **Dependency Audit:** Run `pip-audit` locally to find vulnerable packages. Update `requirements.txt` or `pyproject.toml` to the patched versions.

## Expected Outcomes
- All GitHub Actions workflows return a "Success" status.
- Code matches the repository's excellence standards (PEP8, Type Safety).
- Production deployment gates (11-gate policy) are unlocked.

## Verification Commands
- `ruff check .`
- `mypy src/ main.py scripts/`
- `pytest tests/ --cov=src --cov-fail-under=85`
- `python scripts/verify_version_sync.py` (for release workflows)
- `ls docs/status/PR_TRIAGE_DAILY.md`

## Escalation Path
1. **P2/P3 Failures:** Core Maintainer (@maintainer-quality).
2. **P0/P1 Security:** Security Lead (@xnessom).
3. **Blocked Release:** Release Reliability Engineer (Jules03).

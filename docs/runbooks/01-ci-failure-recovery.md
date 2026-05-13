# Runbook 01: CI Failure Recovery
**Version:** 1.1.0-rc8 | **Last Updated:** 2024-06-12

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
- **Symptoms:** `security-scan`, `gitleaks`, `pip-audit`, or `trivy` jobs fail.
- **Actions:**
  1. **Gitleaks (Secret Detection):** Review the CI log to see which file triggered the alert. **IMMEDIATELY** revoke the leaked secret at the provider and rotate it. Use `git filter-repo` or similar if the secret must be scrubbed from history.
  2. **Trivy (Container Scan):** Check for vulnerable base images or OS packages. Update the `Dockerfile` to use a later patched version of the base image.
  3. **Pip-Audit (Dependency Audit):** Run `pip-audit` locally to find vulnerable packages. Update `requirements.txt` or `pyproject.toml` to the patched versions.
  4. **License Compliance:** If `license-check` fails, ensure all new dependencies are listed in `docs/LICENSE_COMPLIANCE.md`.
  5. **Governance Audit (Gate 4.8):** If `atlas_audit.py` fails, ensure `RISK_LIMITS.md` and `src/core/config.py` are synchronized and all runbooks are present.

## Expected Outcomes
- All GitHub Actions workflows return a "Success" status.
- Code matches the repository's excellence standards (PEP8, Type Safety).
- Production deployment gates (11-gate policy) are unlocked.

## Escalation Path
1. **P2/P3 Failures:** Core Maintainer (@maintainer-quality).
2. **P0/P1 Security:** Security Lead (@xnessom).
3. **Blocked Release:** Release Reliability Engineer (Jules03).

## Verification Commands
```bash
ruff check .
mypy src/ main.py scripts/
pytest tests/ --cov=src --cov-fail-under=85
python scripts/verify_version_sync.py
python scripts/verify_migrations.py
python scripts/validate_env.py
python scripts/atlas_audit.py
pip-audit
ls docs/status/PR_TRIAGE_DAILY.md
```

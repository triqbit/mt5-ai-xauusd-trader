# Runbook 01: CI Failure Recovery

## Description
This runbook provides instructions for recovering from failing GitHub Actions CI jobs.

## Failure Scenarios

### 1. Code Quality (Ruff/Linting)
**Symptom:** CI fails at "Code Quality" job.
**Step-by-step Instructions:**
1. Identify the violation from the CI logs.
2. Run linting locally to reproduce:
   ```bash
   ruff check src/ main.py
   ```
3. Run formatting check locally:
   ```bash
   ruff format --check src/ main.py
   ```
4. Fix violations:
   - For auto-fixable lint issues: `ruff check --fix src/ main.py`
   - For formatting issues: `ruff format src/ main.py`
5. Commit and push changes.

**Expected Outcome:** `ruff check` and `ruff format --check` pass with no errors.

### 2. Dependency Safety (pip-audit)
**Symptom:** CI fails at "Dependency Safety" job due to known CVEs.
**Step-by-step Instructions:**
1. Identify the vulnerable package and CVE ID from CI logs.
2. Run audit locally:
   ```bash
   pip-audit --requirement requirements-ci.txt
   ```
3. Update the package in `requirements.txt` and `requirements-ci.txt` to a patched version.
4. If no patch is available, assess risk or find alternative packages.
5. Commit and push updated requirements.

**Expected Outcome:** `pip-audit` reports "No known vulnerabilities found".

### 3. Tests (pytest)
**Symptom:** CI fails at "Tests" job.
**Step-by-step Instructions:**
1. Identify failing tests from CI logs.
2. Ensure TA-Lib and other dependencies are installed locally.
3. Run tests locally:
   ```bash
   pytest tests/ --cov=src -v
   ```
4. Fix the code or test case causing the failure.
5. Verify coverage meets the required threshold (e.g., >25%).

**Expected Outcome:** All tests pass and coverage threshold is met.

## Escalation Path
1. If linting fails on third-party code: Add exclusion to `pyproject.toml`.
2. If CVE cannot be fixed: Escalate to Security Officer (Jules02).
3. If tests fail due to environment issues: Escalate to Platform Engineer (Jules03).

## Verification Commands
```bash
# Full local CI check
ruff check src/ main.py
ruff format --check src/ main.py
pip-audit --requirement requirements-ci.txt
pytest tests/ --cov=src -v
```

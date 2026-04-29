# Runbook 01: CI Failure Recovery

## Description
This runbook provides instructions for recovering from failures in the GitHub Actions CI pipeline. The pipeline ensures code quality, dependency security, and functional correctness.

## Failure Scenarios

### 1. Code Quality (Ruff) Failure
**Symptoms:** GitHub Action "Code Quality" job fails.
**Cause:** Code does not adhere to linting, formatting, or import sorting rules.

**Steps to Recover:**
1.  Navigate to the repository root.
2.  Run Ruff to identify issues:
    ```bash
    ruff check src/ main.py
    ```
3.  Automatically fix linting violations:
    ```bash
    ruff check --fix src/ main.py
    ```
4.  Apply formatting:
    ```bash
    ruff format src/ main.py
    ```
5.  Verify formatting:
    ```bash
    ruff format --check src/ main.py
    ```
6.  Commit and push the fixes.

**Expected Outcome:** The "Code Quality" job passes on the next push.

---

### 2. Dependency Security (pip-audit) Failure
**Symptoms:** GitHub Action "Dependency Safety" job fails.
**Cause:** One or more dependencies in `requirements-ci.txt` have known vulnerabilities (CVEs).

**Steps to Recover:**
1.  Examine the CI logs to identify the vulnerable package and version.
2.  Run `pip-audit` locally to confirm:
    ```bash
    pip install pip-audit
    pip-audit --requirement requirements-ci.txt
    ```
3.  Update the vulnerable package in `requirements-ci.txt` to a patched version.
4.  If no patch is available, evaluate if the dependency is necessary or if a replacement exists.
5.  Commit the updated `requirements-ci.txt` and push.

**Expected Outcome:** `pip-audit` returns no vulnerabilities.

---

### 3. Test Failure (Pytest)
**Symptoms:** GitHub Action "Tests" job fails.
**Cause:** Code changes broke existing functionality or new tests failed.

**Steps to Recover:**
1.  Check CI logs to identify failing test cases.
2.  Install dependencies locally (including TA-Lib if necessary).
3.  Run tests locally to reproduce the failure:
    ```bash
    PYTHONPATH=. pytest tests/ -v
    ```
4.  Debug the code or update the test if the requirements have changed.
5.  Ensure coverage remains above the required threshold (checked via `--cov=src`).
6.  Commit and push changes.

**Expected Outcome:** All tests pass locally and in CI.

---

## Escalation Path
- **Minor Issues:** Developer responsible for the PR fixes the issue.
- **Persistent CI Infrastructure Issues:** Contact the DevOps/Release Engineering lead (Jules03).
- **Security Vulnerabilities without Patches:** Escalate to the Security Lead (Jules02) for risk assessment.

## Verification Commands
- `ruff check src/ main.py`
- `ruff format --check src/ main.py`
- `pip-audit --requirement requirements-ci.txt`
- `pytest tests/ --cov=src`

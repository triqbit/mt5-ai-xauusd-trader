# Runbook 01: CI Failure Recovery

## Overview
This runbook provides instructions for diagnosing and fixing failures in the GitHub Actions Continuous Integration (CI) pipeline.

## Common Failure Scenarios

### 1. Code Quality (Ruff)
**Symptoms:** The "Code Quality" job fails with linting, formatting, or import sort errors.

**Recovery Steps:**
1.  **Analyze Logs:** Identify the specific files and rules being violated in the GitHub Actions log.
2.  **Auto-fix Linting:** Run Ruff with the `--fix` flag locally.
    ```bash
    ruff check src/ main.py --fix
    ```
3.  **Format Code:** Apply automated formatting.
    ```bash
    ruff format src/ main.py
    ```
4.  **Verify Locally:** Ensure all checks pass before pushing.
    ```bash
    ruff check src/ main.py
    ruff format --check src/ main.py
    ruff check --select I src/ main.py
    ```

### 2. Dependency Safety (pip-audit)
**Symptoms:** The "Dependency Safety" job fails due to known vulnerabilities in third-party packages.

**Recovery Steps:**
1.  **Analyze Logs:** Identify the vulnerable package and the associated CVE.
2.  **Update Dependencies:** Attempt to update the package to a patched version in `requirements.txt` or `requirements-ci.txt`.
3.  **Verify Locally:**
    ```bash
    pip install pip-audit
    pip-audit --requirement requirements-ci.txt
    ```
4.  **Ignore (If applicable):** If the vulnerability is a false positive or has no fix and is acceptable, add an ignore rule (only with security team approval).

### 3. Tests (Pytest)
**Symptoms:** The "Tests" job fails with one or more failing test cases.

**Recovery Steps:**
1.  **Analyze Logs:** Find the failing test name and the traceback.
2.  **Reproduce Locally:** Run the failing test.
    ```bash
    export PYTHONPATH=.
    python -m pytest tests/path/to/test.py
    ```
3.  **Fix Code/Test:** Address the root cause in the application logic or update the test if requirements changed.
4.  **Check Coverage:** Ensure coverage hasn't dropped below the 80% threshold (for pre-prod).
    ```bash
    python -m pytest tests/ --cov=src
    ```

## Escalation Path
1.  **Level 1:** Individual contributor fixing their PR.
2.  **Level 2:** Technical Lead (@maintainer-quality or @andonly1348) for complex architectural failures.
3.  **Level 3:** DevOps/Infrastructure for environment-related CI issues (e.g., TA-Lib installation failure).

## Verification
- GitHub Actions status badge turns green.
- All status checks on the Pull Request show "Passed".

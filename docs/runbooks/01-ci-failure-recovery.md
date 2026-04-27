# Runbook 01: CI Failure Recovery

## Overview
This runbook provides step-by-step instructions for recovering from failing GitHub Actions in the MT5 Trading Bot CI/CD pipeline.

## 1. Failure Identification
When a CI pipeline fails, identify the failing job from the GitHub Actions dashboard:
- **Code Quality**: Ruff linting, formatting, or MyPy type checking issues.
- **Dependency Safety**: Known CVEs found in dependencies by `pip-audit`.
- **Tests**: Unit or integration test failures.
- **Docker Build**: Issues during image construction.

## 2. Recovery Procedures

### 2.1 Code Quality Failures
If the `quality` job fails:
1. **Ruff Linting**: Run `ruff check .` locally to see violations. Use `ruff check --fix .` to auto-fix where possible.
2. **Ruff Format**: Run `ruff format .` to apply standard formatting.
3. **MyPy**: Run `mypy src/` to identify type-hinting issues.
4. **Action**: Commit and push the fixes.

### 2.2 Dependency Safety Failures
If the `security` job fails:
1. Identify the vulnerable package from the `pip-audit` logs.
2. Check if a newer version of the package is available that fixes the CVE.
3. Update `requirements.txt` and `requirements-ci.txt` with the patched version.
4. **Action**: Commit and push the updated requirements.

### 2.3 Test Failures
If the `test` job fails:
1. Review the pytest logs in GitHub Actions to find failing test cases.
2. Reproduce the failure locally: `python -m pytest tests/`.
3. Ensure TA-Lib is installed correctly on the local machine (refer to `ci.yml` for build steps).
4. **Action**: Fix the underlying bug or update the test if the logic change was intentional.

### 2.4 Docker Build Failures
If the `docker` job fails:
1. Check the Docker build logs for syntax errors in the `Dockerfile` or missing build arguments.
2. Verify that all required files are present in the build context.
3. Try building locally: `docker build -t mt5-trader-test .`.

## 3. Escalation Path
- **P3 (Minor Lint/Format)**: Fix within the current PR.
- **P2 (Persistent Test Failures)**: Consult the module owner or senior engineer.
- **P1 (Security Vulnerabilities)**: Immediate attention required; block all deployments until resolved.

## 4. Verification Commands
```bash
# Run all quality checks
ruff check .
ruff format --check .
mypy src/

# Run tests
pytest tests/ --cov=src

# Check dependencies
pip-audit --requirement requirements-ci.txt
```

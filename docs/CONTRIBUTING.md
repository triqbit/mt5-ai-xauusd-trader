# Contributing to MT5 AI/ML Trading Bot

Thank you for your interest in contributing to the MT5 AI/ML Trading Bot project! This document outlines the standards, workflows, and governance for contributing to this enterprise-grade trading system.

## 🏛️ Governance Model

We follow a persona-based governance model (Jules01-Jules05) to ensure specialized focus on different aspects of the system:

- **Jules01 (Product/Core):** Core product feature implementation.
- **Jules02 (Security/Quality):** Hardening, validation, and testing depth.
- **Jules03 (Release/Reliability):** Shippability, governance, and production trust.
- **Jules04 (Quant/AI):** Quant strategy innovation and ML research.
- **Jules05 (Integration/Product):** Merge triage and product coherence.

All contributions must align with these domains and respect the ownership defined in `.github/CODEOWNERS`.

## 🚀 Getting Started

1.  **Fork the repository** and create your branch from `main`.
2.  **Set up your environment:**
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-ci.txt
    ```
3.  **Install pre-commit hooks:**
    ```bash
    pre-commit install
    ```

## 🛠️ Contribution Workflow

### 1. Branching Strategy
- `feat/feature-name`: For new features.
- `fix/bug-name`: For bug fixes.
- `docs/update-name`: For documentation changes.
- `chore/task-name`: For maintenance tasks.

### 2. Pull Request Process
- Ensure your PR follows the `.github/PULL_REQUEST_TEMPLATE.md`.
- Link to the relevant issue in the PR description.
- All PRs require at least one approval from a code owner.
- CI/CD checks (Linting, Tests, Security) must pass.

### 3. Coding Standards
- Follow PEP 8 and the project's Ruff configuration.
- Use type hints for all function signatures and class members.
- Provide Google-style docstrings for all public modules, classes, and methods.
- Maintain a minimum of 25% test coverage for PRs.

### 4. Testing Requirements
- **Unit Tests:** Mandatory for all new logic.
- **Integration Tests:** Required for MT5 connectors or database changes.
- **Coverage:** We aim for >80% coverage for official releases.

Run tests locally:
```bash
python -m pytest
```

## 🛡️ Security Policy

- Never commit secrets (API keys, passwords, private tokens).
- Use `src/core/config.py` for all configurable parameters.
- If you find a security vulnerability, please use the **Security Report** issue template or contact the maintainers privately.

## ⚖️ License Compliance

- Ensure all new dependencies follow the allowed license policy (MIT, Apache 2.0, BSD, etc.).
- Update `ATTRIBUTIONS.md` if you integrate code from external sources.

---
*By contributing to this project, you agree that your contributions will be licensed under its MIT License.*

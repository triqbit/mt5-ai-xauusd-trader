# Contributing to MT5 AI/ML Trading Bot

First off, thank you for considering contributing to this project! It's people like you who make this a great tool for the quantitative trading community.

This project follows an enterprise-grade contribution model to ensure stability, reliability, and auditability of the trading system.

---

## 🏛️ Governance Model

This repository is governed by specialized roles (Personas) to maintain high standards across different domains:

- **Jules01 (Product & Implementation):** Core features and trading engine build work.
- **Jules02 (Security & Validation):** Security hardening, test expansion, and observability.
- **Jules03 (Release & Governance):** Release readiness, compliance, and enterprise controls.
- **Jules04 (Quant & Intelligence):** Strategy innovation and ML research.
- **Jules05 (Orchestration & Triage):** Merge triage and product coherence.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- MetaTrader 5 Terminal (for live/demo execution)
- Docker (optional, for containerized development)

### 2. Development Setup
```bash
# Clone the repository
git clone https://github.com/triqbit/mt5-ai-xauusd-trader.git
cd mt5-ai-xauusd-trader

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -r requirements.txt
pip install ruff mypy pytest pytest-cov
```

---

## 🛠️ Development Workflow

1.  **Branching Strategy:**
    - `main`: Stable production-ready code.
    - `develop`: Integration branch for the next release.
    - Feature branches: `feature/short-description`
    - Bugfix branches: `fix/short-description`
2.  **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/).
3.  **Pull Requests:**
    - Always target the `develop` branch unless it's a critical production fix.
    - Fill out the PR template completely.
    - Ensure CI passes (Linting, Security, Tests).

---

## 📏 Coding Standards

We adhere to the standards defined in [ENTERPRISE_STANDARDS.md](../ENTERPRISE_STANDARDS.md).

### Python Style
- **Linter/Formatter:** We use `ruff`.
- **Type Hints:** Mandatory for all new functions and classes.
- **Docstrings:** Use Google-style docstrings.

### Example
```python
def calculate_risk(balance: float, risk_percent: float) -> float:
    """Calculates the absolute risk amount.

    Args:
        balance: Current account balance.
        risk_percent: Percentage of balance to risk (0.0 to 1.0).

    Returns:
        The calculated risk amount.
    """
    return balance * risk_percent
```

---

## 🧪 Testing Requirements

- **Unit Tests:** Mandatory for all new logic.
- **Coverage:** We aim for high coverage on core modules. PRs that decrease coverage significantly will be flagged.
- **Running Tests:**
  ```bash
  python -m pytest tests/ --cov=src
  ```

---

## 🛡️ Security

Security is paramount in trading systems.
- Do NOT commit `.env` files or any secrets.
- Use `pip-audit` to check for dependency vulnerabilities.
- Follow the guidelines in `SECURITY_FRAMEWORK.md`.

---

## ⚖️ License

By contributing, you agree that your contributions will be licensed under its MIT License.

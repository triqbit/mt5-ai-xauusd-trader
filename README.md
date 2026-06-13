# 🤖 MT5 AI/ML Trading Bot - Enterprise Edition

[![CI Pipeline](https://github.com/triqbit/mt5-ai-xauusd-trader/actions/workflows/ci.yml/badge.svg)](https://github.com/triqbit/mt5-ai-xauusd-trader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**Institutional-Grade Algorithmic Trading System for MetaTrader 5**

---

## 🏛️ Executive Summary

The **MT5 AI/ML Trading Bot** is a production-ready, enterprise-grade automated trading engine specifically optimized for the XAUUSD (Gold) market. It leverages cutting-edge Deep Reinforcement Learning (DRL) and Ensemble Machine Learning to deliver consistent, risk-adjusted returns within the MetaTrader 5 ecosystem.

Built on an architectural foundation that integrates 25+ top-tier quantitative finance repositories, this system provides a unified interface for model training, backtesting, and live execution.

---

## 🏛️ Technical Credibility & Trust

The MT5 AI/ML Trading Bot is built for institutional-grade reliability. We prioritize transparency, evidence-based development, and clear system boundaries.

- **[Architecture Quick-Start](./docs/ARCHITECTURE_QUICK.md):** 5-minute overview of system components, data flow, and maturity levels.
- **[System Maturity Map](./docs/ARCHITECTURE_QUICK.md#🚦-system-maturity-map):** Transparent status of production vs. experimental subsystems.
- **[Technical Health Dashboard](./docs/status/PROJECT_HEALTH.md):** Real-time visibility into technical debt, CI status, and process integrity.
- **[Audit Evidence](./docs/audits/README.md):** Direct routing to verified walk-forward reports, ADRs, and security scorecards.

---

## 🚀 Core Features

### 🧠 Advanced Intelligence
- **DRL Architectures:** PPO (Proximal Policy Optimization), Dreamer V3, and LSTM-based actors.
- **Dynamic Ensemble Engine:** Adaptive model weighting system that adjusts model influence based on real-time performance (Sharpe/Accuracy), confidence calibration, and market regime context.
- **Explainability System:** Structured attribution breakdowns for every trade signal, providing institutional-grade transparency into model and risk decisions.
- **Dynamic Feature Engineering:** 140+ market indicators including multi-timeframe TA-Lib features and macro-sentiment integration.
- **Standardized Model Interface:** All AI models implement a unified `BaseModel` interface for seamless integration and ensemble voting.

### 🛡️ Institutional Risk Management
- **Ray Dalio All-Weather Allocation:** Scenario-based risk parity across multi-currency pairs.
- **9-Layer Execution Filter:** Cascade validation using ATR, Trend Angle, Momentum, EMA sequencing, Session time, Drawdown, Model Stability, Performance, and Confidence.
- **Circuit Breakers:** Automated drawdown protection, per-session loss limits, and daily profit targets.

### ⚡ Production Infrastructure
- **CI/CD Pipeline:** Fully automated GitHub Actions for linting, security audits (`pip-audit`), and unit testing.
- **Startup Configuration Validation:** Mandatory safety gate that blocks execution if production configuration is invalid, incomplete, or contains insecure placeholders.
- **Dockerized Deployment:** Multi-stage builds for lightweight, cross-platform cloud deployment.
- **Hybrid Connector:** Native MT5 SDK support with MetaAPI cloud failover.
- **Enterprise Health Monitoring:** Integrated Liveness and Readiness probes via FastAPI, with automated checks for MT5 connectivity, database health, model integrity, and disk space.

---

## 📊 Performance Benchmark

| Metric | Target Value | Verification Method |
| :--- | :--- | :--- |
| **Annualized Return** | 60% - 90% | Walk-forward Backtest (10Y) |
| **Sharpe Ratio** | 2.8 - 3.5 | Risk-Adjusted Return Analysis |
| **Max Drawdown** | < 12% | Dynamic Equity Protection |
| **Profit Factor** | 2.5+ | Gross Profit / Gross Loss |

---

## 🛠️ Technology Stack

- **Frameworks:** [PyTorch](https://pytorch.org/), [Stable-Baselines3](https://stable-baselines3.readthedocs.io/), [Gymnasium](https://gymnasium.farama.org/)
- **Data:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [TA-Lib](https://github.com/ta-lib/ta-lib-python)
- **DevOps:** [Docker](https://www.docker.com/), GitHub Actions, [Ruff](https://github.com/astral-sh/ruff)
- **Settings:** [Pydantic Settings V2](https://docs.pydantic.dev/latest/usage/pydantic_settings/)

---

## 📦 Project Structure

```text
mt5-ai-xauusd-trader/
├── .github/workflows/    # Automated CI/CD (Quality, Security, Tests)
├── src/                  # Core Package Content
│   ├── core/             # Environment-driven Configuration (Pydantic)
│   ├── models/           # AI/ML Architectures (Ensemble, LSTM, DRL)
│   └── trading/          # MT5 Connectors, Risk Engines & Env
├── tests/                # Comprehensive Unit & Integration Suite
├── main.py               # Unified CLI Entrypoint
├── Dockerfile            # Multi-stage Production Build
└── requirements-ci.txt   # Pinned, CVE-free Dependencies
```

---

## 🏁 Quick Start

### 1. Installation & Verification
```bash
git clone https://github.com/triqbit/mt5-ai-xauusd-trader.git
cd mt5-ai-xauusd-trader

# Install dependencies
pip install -r requirements.txt

# [CRITICAL] Verify environment and dependencies
python main.py --doctor

# Run interactive setup wizard (Recommended)
python main.py --setup

# Perform a pre-flight health check (verifies .env and connectivity)
python main.py --check
```

### 2. Configuration
The system features an **Interactive Setup Wizard**. Simply run the bot, and it will offer to guide you through the configuration:
```bash
python main.py
```

Alternatively, create a `.env` file manually:
```env
MT5_LOGIN=your_account
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server
MODE=demo
```

### 3. Execution
The CLI is designed to be **resilient**. Diagnostic commands work even if dependencies are not yet installed:

```bash
# Get help and usage examples (always available)
python main.py --help

# Verify environment and dependencies
python main.py --doctor

# Show current sanitized configuration
python main.py --show-config

# Perform a pre-flight health check (connectivity, database, models)
python main.py --check

# Start trading in demo mode (CLI flags override .env)
python main.py --mode demo --symbol XAUUSD --algo ensemble

# Start live trading (requires explicit confirmation)
python main.py --mode live --algo ensemble --confirm-live
```

---

## 📜 Documentation Index

| Guide | Description |
| :--- | :--- |
| [**Architecture Quick-Start**](./docs/ARCHITECTURE_QUICK.md) | **Primary technical overview and system maturity map.** |
| [**Pre-Production Checklist**](./docs/PREPROD_CHECKLIST.md) | **Mandatory deployment gate checklist for production releases.** |
| [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | Technical roadmap and implementation milestones. |
| [ENTERPRISE_STANDARDS.md](./ENTERPRISE_STANDARDS.md) | Coding standards, CI/CD requirements, and security policies. |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Step-by-step instructions for Docker and Cloud deployment. |
| [DATABASE_STANDARDS.md](./DATABASE_STANDARDS.md) | Schemas for trade logging and performance tracking. |
| [**SLO & Reliability Targets**](./docs/SLO_TARGETS.md) | **Measurable reliability standards and error budget framework.** |
| [**Contributing Guide**](./docs/CONTRIBUTING.md) | **How to contribute safely and effectively.** |
| [**Contribution Map**](./docs/CONTRIBUTION_MAP.md) | **Safe vs. Sensitive zone navigation.** |
| [**First Contribution**](./docs/FIRST_REAL_CONTRIBUTION.md) | **Step-by-step guide for your first PR.** |
| [**Data Retention Policy**](./docs/DATA_RETENTION_POLICY.md) | **Policies for operational data retention and automated purging.** |
| [**Disaster Recovery Plan**](./docs/DISASTER_RECOVERY.md) | **Procedures for database, log, and operational data recovery.** |

---

## 🤝 Contributing

We welcome contributions! To ensure safety in this high-turbulence repository:

1.  **Start in a [Safe Zone](./docs/CONTRIBUTION_MAP.md#🟢-safe-zones-recommended-for-first-prs):** Focus on `docs/`, `tests/`, or `scripts/`.
2.  **Follow the [First Real Contribution](./docs/FIRST_REAL_CONTRIBUTION.md) guide:** A step-by-step path to your first PR.
3.  **Mandatory Rebase:** Always rebase your branch on the latest `main` graft before submitting.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full workflow and governance rules.

---

## ⚖️ License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

**Disclaimer:** *Trading involves significant risk. This software is for educational purposes only. The developers assume no liability for financial losses.*

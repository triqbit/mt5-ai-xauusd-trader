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

## 🚀 Core Features

### 🧠 Advanced Intelligence
- **DRL Architectures:** PPO (Proximal Policy Optimization), Dreamer V3, and LSTM-based actors.
- **Ensemble Engine:** Real-time signal consensus from multiple neural networks to minimize variance.
- **Dynamic Feature Engineering:** 140+ market indicators including multi-timeframe TA-Lib features and macro-sentiment integration.

### 🛡️ Institutional Risk Management
- **The Guardian’s Gate:** Automated pre-flight system checks (MT5, DB, Models) to prevent failed live starts.
- **Ray Dalio All-Weather Allocation:** Scenario-based risk parity across multi-currency pairs.
- **6-Layer Execution Filter:** Cascade validation using ATR, Trend Angle, Momentum, and EMA sequencing.
- **Circuit Breakers:** Automated drawdown protection, per-session loss limits, and daily profit targets.

### ⚡ Production Infrastructure
- **CI/CD Pipeline:** Fully automated GitHub Actions for linting (Ruff), Type Safety (Mypy), security audits (`pip-audit`), and unit testing.
- **Dockerized Deployment:** Multi-stage builds for lightweight, cross-platform cloud deployment.
- **Hybrid Connector:** Native MT5 SDK support with MetaAPI cloud failover.

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
- **DevOps:** [Docker](https://www.docker.com/), GitHub Actions, [Ruff](https://github.com/astral-sh/ruff), [Mypy](https://mypy.readthedocs.io/)
- **Settings:** [Pydantic Settings V2](https://docs.pydantic.dev/latest/usage/pydantic_settings/)

---

## 📦 Project Structure

```text
mt5-ai-xauusd-trader/
├── .github/workflows/    # Automated CI/CD (Quality, Security, Tests)
├── docs/                 # Detailed architectural documentation
├── src/                  # Core Package Content
│   ├── core/             # Configuration & Pre-flight Checks (The Guardian's Gate)
│   ├── models/           # AI/ML Architectures (Ensemble, LSTM, DRL)
│   └── trading/          # MT5 SDK Connectors & Risk Engines
├── tests/                # Comprehensive Unit & Integration Suite
├── main.py               # Unified CLI Entrypoint
├── Dockerfile            # Multi-stage Production Build
└── requirements-ci.txt   # Pinned, CVE-free Dependencies
```

---

## 🏁 Quick Start

### 1. Installation
```bash
git clone https://github.com/triqbit/mt5-ai-xauusd-trader.git
cd mt5-ai-xauusd-trader
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file based on `src/core/config.py` defaults:
```env
MT5_LOGIN=your_account
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server
MODE=demo
```

### 3. Execution
```bash
# Run validation and start in demo mode
python main.py --mode demo --symbol XAUUSD --verbose
```

---

## 📜 Documentation Index

| Guide | Description |
| :--- | :--- |
| [DEVELOPMENT_PLAN.md](./docs/DEVELOPMENT_PLAN.md) | Technical roadmap and implementation milestones. |
| [ENTERPRISE_STANDARDS.md](./docs/ENTERPRISE_STANDARDS.md) | Coding standards, CI/CD requirements, and security policies. |
| [DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md) | Step-by-step instructions for Docker and Cloud deployment. |
| [DATABASE_STANDARDS.md](./docs/DATABASE_STANDARDS.md) | Schemas for trade logging and performance tracking. |
| [ROLLBACK.md](./docs/ROLLBACK.md) | Emergency rollback procedures and safety protocols. |

---

## ⚖️ License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

**Disclaimer:** *Trading involves significant risk. This software is for educational purposes only. The developers assume no liability for financial losses.*

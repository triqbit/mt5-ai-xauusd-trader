# 🏛️ Architecture Quick-Start

This guide provides a high-level overview of the MT5 AI/ML Trading Bot architecture, system maturity, and evidence routing for technical stakeholders.

## 🏗️ System Overview

The system is designed as a modular, event-driven trading engine that separates market intelligence from execution and risk management.

### Core Components

| Layer | Responsibility | Key Modules |
| :--- | :--- | :--- |
| **Intelligence** | Market regime detection, signal generation, and ensemble consensus. | `src/models/`, `src/environment/` |
| **Execution** | MT5 lifecycle management, order execution, and connectivity. | `src/trading/mt5_connector.py` |
| **Risk & Allocation** | Position sizing, drawdown protection, and capital allocation. | `src/trading/risk_manager.py`, `src/trading/capital_allocator.py` |
| **Infrastructure** | Config validation, health monitoring, and trade logging. | `src/core/` |
| **Research** | Backtesting, stress testing, and model evaluation. | `src/research/`, `src/analytics/` |

---

## 🚦 System Maturity Map (May 2026)

This map identifies the production readiness of various subsystems to ensure transparent expectations for contributors and operators.

| Subsystem | Maturity | Status |
| :--- | :--- | :--- |
| **Configuration Engine** | 🟢 Production | Pydantic-driven, environment-validated. |
| **MT5 Connectivity** | 🟢 Production | Stable SDK integration with failover support. |
| **Risk Management** | 🟢 Production | 6-layer `ExecutionFilter` and circuit breakers fully operational. |
| **Ensemble Models** | 🟢 Production | `EnsembleModel` (LSTM + PPO) integrated and validated. |
| **Decision Support** | 🟢 Production | Institutional Cockpit (TUI) providing full signal attribution. |
| **Capital Allocation** | 🟡 Release Candidate | Institutional allocation active; multi-symbol scaling in final test. |
| **RL Training Pipeline** | 🔵 Experimental | Active research into Dreamer V3 and Transformer actors. |
| **Explainability Engine** | 🟢 Production |attribution reporting functional in live loop via `SignalExplainer`. |

---

## 🗺️ Data & Logic Flow

1.  **Ingestion:** `MT5Connector` fetches real-time tick and OHLC data.
2.  **Transformation:** `FeatureEngineering` computes 140+ technical indicators.
3.  **Intelligence:** `RegimeDetector` classifies market state; `EnsembleModel` generates a consensus signal.
4.  **Risk Gate:** `RiskManager` validates signal; `ExecutionFilter` applies the 6-layer cascade.
5.  **Allocation:** `CapitalAllocator` determines lot size based on institutional risk limits.
6.  **Execution:** `MT5Connector` dispatches the order and monitors for fills.
7.  **Observability:** `TradeLogger` records details; `Monitor` pushes metrics to Prometheus; `DecisionSupportSystem` renders the cockpit.

---

## 🔍 Evidence & Audit Routing

- **Architecture Decisions:** `docs/audits/ADR_AUDIT_REPORT.md`
- **Security & Compliance:** `docs/audits/SECURITY_HARDENING_v1.md`
- **System Health:** `docs/status/EXECUTIVE_SUMMARY.md`
- **Product Coherence:** `docs/quality/PRODUCT_COHERENCE_AUDIT.md`

---

## 🛠️ Developer Entry Points

- **Health Check:** `make doctor`
- **First Run:** `make init && make demo`
- **Verification:** `make test && make lint`
- **Backtesting:** `make backtest`

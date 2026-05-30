# 🏛️ Architecture Quick-Start

This guide provides a high-level overview of the MT5 AI/ML Trading Bot architecture, system maturity, and evidence routing for technical stakeholders.

## 🏗️ System Overview

The system is designed as a modular, event-driven trading engine that separates market intelligence from execution and risk management.

### Core Components

| Layer | Responsibility | Key Modules |
| :--- | :--- | :--- |
| **Intelligence** | Market regime detection, directional signal generation, and ensemble consensus. | `src/models/`, `src/environment/` |
| **Execution** | MT5 lifecycle management, order execution, and connectivity. | `src/trading/mt5_connector.py` |
| **Risk & Allocation** | Position sizing, drawdown protection, and capital allocation. | `src/trading/risk_manager.py`, `src/trading/capital_allocator.py` |
| **Infrastructure** | Config validation, health monitoring, and trade logging. | `src/core/` |
| **Research** | Backtesting, stress testing, and model evaluation. | `src/research/`, `src/analytics/` |

---

## 🚦 System Maturity Map

This map identifies the production readiness of various subsystems to ensure transparent expectations for contributors and operators.

| Subsystem | Maturity | Status |
| :--- | :--- | :--- |
| **Configuration Engine** | 🟢 Production | Pydantic-driven, environment-validated. |
| **MT5 Connectivity** | 🟢 Production | Stable SDK integration with failover support. |
| **Risk Management** | 🟢 Production | 10-layer cascade verified with high stability. |
| **Ensemble Models** | 🟢 Production | Backtest-validated; institutional calibration active. |
| **RL Training Pipeline** | 🔵 Experimental | Active research into Transformer-based actors. |
| **Decision Support** | 🟢 Production | Structured decision packets and operator dashboard active. |
| **Explainability Engine** | 🟢 Production | Institutional attribution reporting and TUI integration verified. |

---

## 🗺️ Data & Logic Flow

1.  **Ingestion:** `MT5Connector` fetches real-time tick and OHLC data.
2.  **Transformation:** `FeatureEngineering` computes 140+ technical and sentiment indicators.
3.  **Intelligence:** `RegimeDetector` classifies market state; `DynamicEnsemble` generates a directional signal.
4.  **Risk Gate:** `RiskManager` and `ExecutionFilter` validate the signal against a 10-layer cascade: ATR Volatility, Trend Angle, EMA Sequence, Momentum, Session/Time, Drawdown, Model Stability, Performance, Confidence, and Signal Consistency (Flicker Guard).
5.  **Allocation:** `CapitalAllocator` determines optimal lot size based on equity and regime.
6.  **Execution:** `MT5Connector` dispatches the order and monitors for fills/slippage.
7.  **Observability:** `TradeLogger` records execution details; `Monitor` pushes metrics to Prometheus.

---

## 🔍 Evidence & Audit Routing

Use these paths to find technical evidence and audit reports:

- **Architecture Decisions:** (See `docs/audits/ADR_AUDIT_REPORT.md` - *Upcoming*)
- **Security & Compliance:** `docs/audits/ENTERPRISE_EVIDENCE_SCORECARD.md`
- **System Health:** `docs/status/PROJECT_HEALTH.md`
- **Performance Benchmarks:** `docs/audits/PERFORMANCE_COMPLEXITY_REPORT.md` (*Upcoming*)
- **Integration Status:** `docs/status/PROCESS_INTEGRITY_LOG.md`

---

## 🛠️ Developer Entry Points

- **Health Check:** `make doctor`
- **First Run:** `make bootstrap && make demo`
- **Verification:** `make test && make lint`
- **Strategy Research:** `src/research/stress_lab.py`

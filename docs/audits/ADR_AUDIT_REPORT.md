# 🏛️ Architecture Decision Record (ADR) Audit Report

This report documents the key architectural decisions governing the MT5 AI/ML Trading Bot, providing verified evidence for technical stakeholders and institutional auditors.

---

## 📋 Executive Summary of Decisions

| Decision | Area | Status | Verified Evidence |
| :--- | :--- | :--- | :--- |
| **Pydantic V2 Configuration** | Infrastructure | ✅ Verified | `src/core/config.py` |
| **Immutable Schema Design** | Data Integrity | ✅ Verified | `src/core/schemas.py` |
| **Unified Model Interface** | Intelligence | ✅ Verified | `src/models/base_model.py` |
| **11-Layer Execution Filter** | Execution | ✅ Verified | `src/trading/execution_filter.py` |
| **Central Risk Authority** | Risk | ✅ Verified | `src/trading/risk_manager.py` |
| **Dual-Path Connectivity** | Connectivity | ✅ Verified | `src/trading/mt5_connector.py` |

---

## 🏗️ Detailed Audit of Key Decisions

### 1. Pydantic V2 Configuration Engine
- **Decision:** Use `pydantic-settings` (V2) for centralized, type-safe, and environment-driven configuration.
- **Rationale:** Ensures that invalid configurations (e.g., risk > 2%) block system startup, reducing operational tail risk.
- **Evidence:** `src/core/config.py` implements `TradingConfig(BaseSettings)` with `@field_validator` for safety gates.

### 2. Immutable Schema Design (Frozen Models)
- **Decision:** All core data structures (`TradeSignal`, `ExecutionDecision`) use `frozen=True` and `extra="forbid"`.
- **Rationale:** Prevents downstream components from altering model signals or risk decisions, ensuring a tamper-proof audit trail for forensic analysis.
- **Evidence:** `src/core/schemas.py` defines `TradeSignal` and `ExecutionDecision` with `ConfigDict(frozen=True)`.

### 3. Unified Model Interface (BaseModel)
- **Decision:** Enforce a strict Abstract Base Class (`BaseModel`) for all AI/ML models.
- **Rationale:** Decouples model research (RL, LSTM, Transformers) from the trading pipeline, allowing for seamless ensemble integration and standardized evaluation.
- **Evidence:** `src/models/base_model.py` defines the `predict` abstract method and `Signal` named tuple.

### 4. 11-Layer Execution Filter Cascade
- **Decision:** Implement a multi-stage validation cascade (ATR, Trend, EMA, Momentum, Session, Drawdown, etc.) before order dispatch.
- **Rationale:** Provides defense-in-depth against "rogue" model signals that may be technically valid but contextually unsafe (e.g., high-volatility spikes).
- **Evidence:** `src/trading/execution_filter.py` implements `ExecutionFilter.validate()` with 11 distinct evaluation layers.

### 5. Central Risk Authority (RiskManager)
- **Decision:** A single `RiskManager` class acts as the final arbiter for all trade approvals, using fractional Kelly sizing and Ray Dalio All-Weather weights.
- **Rationale:** Centralizes risk logic to prevent fragmented or inconsistent risk calculation across multiple models or symbols.
- **Evidence:** `src/trading/risk_manager.py` implements the `approve()` method and `size_position()` using Kelly Criterion.

### 6. Dual-Path Connectivity (Native + Cloud)
- **Decision:** Support both native `MetaTrader5` SDK (Windows) and `metaapi-cloud-sdk` (Mac/Linux/Cloud) fallback.
- **Rationale:** Maximizes deployment flexibility and ensures connectivity resilience across diverse environment architectures.
- **Evidence:** `src/trading/mt5_connector.py` implements a primary/fallback logic in the `initialize()` method.

---

## 🏛️ Governance Context

This ADR Audit Report is maintained by **Jules06 (Technical Credibility & Evidence Surface Engine)**. It is updated weekly to reflect the current verified state of the repository's architectural foundation.

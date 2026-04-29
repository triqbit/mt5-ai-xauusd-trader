# 🗺️ MT5 AI/ML Trading Bot - Strategic Feature Roadmap

This roadmap outlines the evolution of the MT5 AI XAUUSD trader from a functional baseline to an institutional-grade autonomous system.

## 📊 System Maturity Audit (April 2026)

| Category | Score | Current State | Target (v1.5) |
| :--- | :---: | :--- | :--- |
| **Product Capability** | 6/10 | Core execution & ensemble inference active. | Multi-regime strategy switching. |
| **Usability** | 4/10 | CLI-based; manual model management. | Integrated TUI Cockpit & Auto-calibration. |
| **Safety** | 7/10 | Hard circuit breakers & 6-layer risk filters. | Predictive regime-based halts. |
| **Intelligence** | 6/10 | PPO/LSTM Ensemble with Sharpe-weighted voting. | Explainable AI (XAI) & Macro-sensitivity. |
| **Differentiation** | 5/10 | XAUUSD focus with technical ensemble. | Gold-specific macro-sentinel logic. |

---

## 🔴 High Priority (Next 2 Weeks)

### 1. High-Fidelity Backtesting & Crisis Validator
- **Score:** 10/10
- **Cost:** M
- **Dependency Readiness:** ✅ High (Infrastructure exists)
- **Operational Leverage:** High (Reduces live capital risk)
- **Value:** Solves the "black box" risk. Allows validation against historical events like the 2020 crash and 2022 inflation spikes.
- **Why:** The codebase currently lacks a unified, reproducible backtesting suite that accounts for variable spreads and slippage.

### 2. Regime-Aware Execution Filters (Dynamic Circuit Breakers)
- **Score:** 9.5/10
- **Cost:** M
- **Dependency Readiness:** ✅ High
- **Operational Leverage:** High (Prevents "bleeding" in bad markets)
- **Value:** Prevents the AI from trading during high-impact news (NFP, FOMC) or low-liquidity gaps where technical patterns break down.
- **Why:** Safety is the highest institutional priority. Static filters are insufficient for Gold's volatility.

---

## 🟡 Medium Priority (Weeks 3-4)

### 3. Gold-Specific Macro Sensitivity Overlay
- **Score:** 9/10
- **Cost:** L
- **Dependency Readiness:** ⚠️ Medium (Requires reliable Macro API integration)
- **Operational Leverage:** High (Adds unique alpha)
- **Value:** Infuses the bot with "market common sense" (e.g., DXY strength usually hurts Gold).
- **Why:** Purely technical RL models often miss major fundamental shifts. This provides a "fundamental anchor."

### 4. Explainable Decision Cockpit (TUI)
- **Score:** 8.5/10
- **Cost:** M
- **Dependency Readiness:** ✅ High
- **Operational Leverage:** Medium (Speeds up debugging)
- **Value:** Provides a real-time dashboard showing *why* the ensemble chose to Buy/Sell (Feature Importance maps).
- **Why:** Trust is built through transparency. A CLI log is insufficient for high-stakes monitoring.

---

## ⚪ Future Consideration

### 5. Federated Ensemble Retraining
- **Score:** 7/10 | **Cost:** XL | **Rationale:** Allowing the bot to adapt online to changing market microstructures without full redeploys.

### 6. Multi-Broker Liquidity Aggregation
- **Score:** 6/10 | **Cost:** L | **Rationale:** Executing across multiple MT5 accounts to minimize market impact on larger lot sizes.

---

## 📐 Prioritization Matrix

| Feature | Strategic Importance | Implementation Cost | Leverage | Priority |
| :--- | :---: | :---: | :---: | :--- |
| **HF Backtesting** | 10 | M | ⚡ High | **CRITICAL** |
| **Regime Filters** | 9 | M | ⚡ High | **HIGH** |
| **Macro Overlay** | 9 | L | ⚡ High | **HIGH** |
| **Decision Cockpit**| 8 | M | 🟢 Med | **MEDIUM** |
| **Auto-Calibration**| 7 | L | 🟢 Med | **LOW** |

---

**Last Updated:** April 2026
**Approved By:** Jules05 (Product Steward)

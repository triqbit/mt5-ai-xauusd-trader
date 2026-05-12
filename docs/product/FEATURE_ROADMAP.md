# 🗺️ Strategic Feature Roadmap - May 14, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest maturity assessment following the Jules01-05 product coherence and risk harmonization.

---

## 📊 Repo Maturity Assessment (May 14, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8.2/10 | **Status:** 11-layer `ExecutionFilter` and harmonized `AuditedRiskManager` are fully integrated. **Gap:** Real-time feedback loop for slippage-based execution adjustment is missing. |
| **Usability** | 🟢 7.5/10 | **Status:** Decision Cockpit TUI is institutional-grade with structured risk rejection reasons. **Gap:** Remote management and human-in-the-loop signal approval (Telegram) are not yet active. |
| **Safety** | 🟢 8.5/10 | **Status:** 8-layer risk cascade and capital allocation are structurally enforced via a unified `RiskDecision` interface. **Gap:** "Flatten & Fence" (Emergency Kill Switch) remains a verified stub in the Makefile. |
| **Intelligence** | 🟢 7.0/10 | **Status:** Regime stability scoring and feature engineering (140+) are live. **Gap:** live trading loop still relies on stubs for real-time Macro Risk (FRED/YFinance). |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** "Glass Box" transparency and auditability are repo-wide standards. **Gap:** Specialized gold-specific macro overlays (Real Yields/DXY) are not yet active. |

---

## 🚀 High Priority (Next 2 Weeks)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 10/10 | Cost: M | Why: XAUUSD is fundamentally driven by US Real Yields and DXY. Moving from stubs to live FRED/YFinance data for signal vetoing is the highest-value intelligence upgrade.
  - *Strategic Importance:* 10/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`src/data/event_intelligence.py` logic is mature)
  - *Operational Leverage:* Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - *Value:* Solves "Technical-only" blindness during Fed pivots and news-driven spikes.

- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.5/10 | Cost: S | Why: Currently a Makefile stub. Implementing a robust, multi-channel command to close all positions, cancel orders, and lock trading is the final safety mile for institutional trust.
  - *Strategic Importance:* 9.5/10
  - *Implementation Cost:* S
  - *Dependency Readiness:* 🟢 High (MT5 connector supports position management)
  - *Operational Leverage:* High (Foundational for capital preservation and compliance)
  - *Value:* Instant capital protection during catastrophic market/system events.

- **Telegram Interactive Command Center** — Score: 9.0/10 | Cost: M | Why: Port the Decision Cockpit to Telegram with "Approve/Reject" buttons. Enables mobile-first institutional oversight and human-in-the-loop risk management.
  - *Strategic Importance:* 9.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium (Requires bot gateway and session management)
  - *Operational Leverage:* High (Increases mobility and operator response time)
  - *Value:* Eliminates the need for constant terminal monitoring; provides secure remote control.

## ⚖️ Medium Priority (Weeks 3-4)

- **Adaptive Execution Feedback Loop (Slippage-Aware)** — Score: 8.5/10 | Cost: M | Why: Use realized slippage from `TradeLogger` to dynamically adjust `ExecutionFilter` thresholds.
  - *Strategic Importance:* 8.5/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`ExecutionQuality` schema and logging are active)
  - *Operational Leverage:* Medium (Optimizes fill probability in changing liquidity conditions)
  - *Value:* Automatically "backs off" during periods of toxic liquidity or broker performance degradation.

- **Gold-specific Macro Sensitivity Overlays** — Score: 8.0/10 | Cost: M | Why: Quantify XAUUSD sensitivity to US 10Y Real Yields and DXY in real-time.
  - *Strategic Importance:* 8.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (Requires Live Macro Intelligence as a prerequisite)
  - *Operational Leverage:* High (Differentiates from generic retail bots via First-Principles analysis)
  - *Value:* Provides a fundamental "Anchor" to technical ensemble signals.

## 🔭 Future Consideration

- **Institutional Gold Flow & Physical Demand Proxies** — Score: 7.5/10 | Cost: L | Why: Track ETF flows (GLD/IAU) and Shanghai premiums to detect physical/paper divergences.
  - *Strategic Importance:* 7.5/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟢 High
  - *Value:* Provides visibility into "Smart Money" accumulation vs. retail speculative churn.

- **Trade Narrative Memory (LLM-Enhanced)** — Score: 7.2/10 | Cost: L | Why: Qualitative "Why?" analysis for every trade using LLM synthesis of regime, macro, and execution data.
  - *Strategic Importance:* 7.0/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium (Requires LLM API integration)
  - *Value:* Automates institutional post-trade journaling and alpha discovery.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

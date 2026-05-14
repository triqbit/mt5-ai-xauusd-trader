# 🗺️ Strategic Feature Roadmap - May 15, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest maturity assessment and the 13-area anti-friction strategy.

---

## 📊 Repo Maturity Assessment (May 15, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8.5/10 | **Status:** 11-layer `ExecutionFilter`, `AuditedRiskManager`, and `DecisionSupportSystem` are fully integrated. `ExecutionAnalyzer` is live for post-trade analysis. **Gap:** Real-time feedback loop from `ExecutionAnalyzer` to `ExecutionFilter` (slippage-veto) is not yet active. |
| **Usability** | 🟢 7.8/10 | **Status:** Decision Cockpit TUI is institutional-grade. `TradeLogger` provides high-fidelity persistence. **Gap:** Telegram Interactive Gateway lacks signal approval flow ("Approve/Reject"). |
| **Safety** | 🟢 8.7/10 | **Status:** 8-layer risk cascade and capital allocation are structurally enforced. Risk core is harmonized. **Gap:** "Flatten & Fence" (Emergency Kill Switch) remains a verified stub in the Makefile/scripts. |
| **Intelligence** | 🟢 7.5/10 | **Status:** Regime stability scoring and 140+ feature engineering are live. `EventIntelligence` has multi-provider logic ready. **Gap:** `main.py` live loop still uses stubs for real-time Macro Risk (FRED/YFinance). |
| **Market Differentiation** | 🟢 8.8/10 | **Status:** "Glass Box" transparency and signal attribution are repo-wide standards. Feature 12 (Sentiment Intelligence) is formally defined. **Gap:** Gold-specific macro overlays and sentiment data feeds are not yet active. |

---

## 🚀 High Priority (Next 2 Weeks)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 9.8/10 | Cost: M | Why: XAUUSD is fundamentally driven by US Real Yields and DXY. Moving from stubs to live FRED/YFinance data for signal vetoing is the highest-value intelligence upgrade.
  - *Strategic Importance:* 10/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`src/data/event_intelligence.py` logic is mature)
  - *Operational Leverage:* Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - *End-user Value:* Solves fundamental blindness during Fed pivots and news-driven spikes.

- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.6/10 | Cost: S | Why: Currently a Makefile stub. Implementing a robust, multi-channel command to close all positions, cancel orders, and lock trading is the final safety mile for institutional trust.
  - *Strategic Importance:* 9.8/10
  - *Implementation Cost:* S
  - *Dependency Readiness:* 🟢 High (MT5 connector supports position management)
  - *Operational Leverage:* High (Foundational for capital preservation and compliance)
  - *End-user Value:* Instant capital protection during catastrophic market/system events.

- **Telegram Interactive Command Center (Human-in-the-Loop)** — Score: 9.3/10 | Cost: M | Why: Port the Decision Cockpit to Telegram with "Approve/Reject" buttons. Enables mobile-first institutional oversight and human-in-the-loop risk management.
  - *Strategic Importance:* 9.2/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium (Requires bot gateway integration into the live loop)
  - *Operational Leverage:* High (Increases mobility and operator response time)
  - *End-user Value:* Eliminates the need for constant terminal monitoring; provides secure remote control.

## ⚖️ Medium Priority (Weeks 3-4)

- **Institutional Sentiment & Positioning Intelligence (Alpha)** — Score: 8.8/10 | Cost: M | Why: Implement the data harvesting for CFTC COT and retail sentiment ratios. Detect "crowded trades" to apply a contrarian veto.
  - *Strategic Importance:* 9.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (Feature 12 is already defined and scoped)
  - *Operational Leverage:* High (Strong differentiation via "Crowded Trade Detection")
  - *End-user Value:* Prevents entering late-stage exhausted trends.

- **Adaptive Execution Feedback Loop (Slippage-Aware)** — Score: 8.7/10 | Cost: M | Why: Use realized slippage from `ExecutionAnalyzer` to dynamically adjust `ExecutionFilter` thresholds.
  - *Strategic Importance:* 8.5/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`ExecutionQuality` metrics are already logged)
  - *Operational Leverage:* Medium (Optimizes fill probability in changing liquidity conditions)
  - *End-user Value:* Automatically "backs off" during periods of toxic liquidity or broker performance degradation.

- **Gold-specific Macro Sensitivity Overlays (Real Yields/DXY)** — Score: 8.4/10 | Cost: M | Why: Quantify XAUUSD sensitivity to US 10Y Real Yields and DXY in real-time.
  - *Strategic Importance:* 8.2/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (Prerequisite: Live Macro Intelligence Pipeline)
  - *Operational Leverage:* High (Differentiates from generic retail bots via First-Principles analysis)
  - *End-user Value:* Provides a fundamental "Anchor" to technical ensemble signals.

## 🔭 Future Consideration

- **Institutional Gold Flow & Physical Demand Proxies** — Score: 7.8/10 | Cost: L | Why: Track ETF flows (GLD/IAU) and Shanghai premiums to detect physical/paper divergences.
  - *Strategic Importance:* 7.8/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟢 High
  - *End-user Value:* Provides visibility into "Smart Money" accumulation vs. retail speculative churn.

- **Trade Narrative Memory (LLM-Enhanced)** — Score: 7.5/10 | Cost: L | Why: Qualitative "Why?" analysis for every trade using LLM synthesis of regime, macro, and execution data.
  - *Strategic Importance:* 7.5/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium (Requires LLM API integration)
  - *End-user Value:* Automates institutional post-trade journaling and alpha discovery.

- **Autonomous Parameter Self-Optimization** — Score: 7.2/10 | Cost: XL | Why: Use RL or Bayesian Optimization to dynamically tune `ExecutionFilter` and `RiskManager` parameters based on realized PnL.
  - *Strategic Importance:* 8.0/10
  - *Implementation Cost:* XL
  - *Dependency Readiness:* 🔴 Low (Requires significant research and stability testing)
  - *Operational Leverage:* High (Moves system towards full autonomy)
  - *End-user Value:* Eliminates manual "tuning" of risk thresholds.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

# 🗺️ Strategic Feature Roadmap - May 13, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest maturity assessment following the Jules01-04 lifecycle harmonization.

---

## 📊 Repo Maturity Assessment (May 13, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8.0/10 | **Status:** `RiskManager` and `CapitalAllocator` are fully harmonized. **Gap:** Execution feedback loop for real-time slippage adjustment is missing. |
| **Usability** | 🟢 7.2/10 | **Status:** Decision Cockpit TUI is robust. **Gap:** Remote/mobile interactivity is currently restricted to passive logging. |
| **Safety** | 🟢 8.8/10 | **Status:** 8-layer cascading risk filter is integrated and verified. **Gap:** Automated "Flatten & Fence" (Emergency Kill Switch) remains a verified stub. |
| **Intelligence** | 🟡 6.8/10 | **Status:** Regime stability scoring is architected. **Gap:** System is still "Macro Blind" to real-time US Treasury and DXY shifts. |
| **Market Differentiation** | 🟢 8.2/10 | **Status:** "Glass Box" transparency is structurally enforced. **Gap:** Gold-specific macro overlays and liquidity heatmaps are not yet active. |

---

## High Priority (Next 2 Weeks)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 10/10 | Cost: M | Why: XAUUSD is fundamentally driven by US Real Yields and DXY. Vetoing technical signals that conflict with macro reality is the highest-value intelligence upgrade.
  - *Strategic Importance:* 10/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`src/data/event_intelligence.py` exists)
  - *Operational Leverage:* Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - *End-user/Operator Value:* Solves the primary pain of "Technical-only" blindness during Fed pivots.

- **Production-Grade Emergency Kill Switch** — Score: 9.5/10 | Cost: S | Why: Currently a verified stub (`make emergency-stop`). Implementing "Flatten & Fence" (close all, cancel all, lock accounts) is critical for institutional safety.
  - *Strategic Importance:* 9.5/10
  - *Implementation Cost:* S
  - *Dependency Readiness:* 🟢 High (MT5/MetaAPI hooks verified)
  - *Operational Leverage:* High (Foundational for capital preservation)
  - *End-user/Operator Value:* Instant recovery from catastrophic market events or system failures.

- **Adaptive Capital-Preservation Operating Modes** — Score: 9.0/10 | Cost: M | Why: Dynamic postures (Defensive, Balanced, Aggressive) that adjust sizing and filters globally.
  - *Strategic Importance:* 9.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (RiskManager architecture supports dynamic overrides)
  - *Operational Leverage:* High (Automates risk-off during high-uncertainty regimes)
  - *End-user/Operator Value:* Eliminates manual parameter tweaking during news events.

## Medium Priority (Weeks 3-4)

- **Telegram Interactive Command Center** — Score: 9.0/10 | Cost: M | Why: Port the Decision Cockpit to Telegram with "Approve/Reject" buttons for human-in-the-loop oversight.
  - *Strategic Importance:* 9.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium (Requires bot gateway implementation)
  - *Operational Leverage:* High (Increases mobility and response time)
  - *End-user/Operator Value:* Eliminates the need for 24/7 terminal monitoring; provides remote safety controls.

- **Institutional Liquidity & Order Flow Heatmap** — Score: 8.5/10 | Cost: L | Why: Use DOM data to detect institutional liquidity pools and avoid "Liquidity Gaps."
  - *Strategic Importance:* 8.5/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium (Requires MT5 Level 2 data streaming)
  - *Operational Leverage:* High (Leading indicator for reversals)
  - *End-user/Operator Value:* Provides visibility into "Smart Money" positioning vs. retail traps.

- **Adaptive Position Sizing (Regime Stability)** — Score: 8.2/10 | Cost: M | Why: Scale lot sizes based on the persistence and confidence of the market regime.
  - *Strategic Importance:* 8.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`RegimeDetector` stability scores exist)
  - *Operational Leverage:* High (Optimizes capital efficiency across cycles)
  - *End-user/Operator Value:* Automatically "leans in" during stable trends and "steps back" during fragile transitions.

## Future Consideration

- **Institutional What-If Execution Simulator** — Score: 8.0/10 | Cost: M | Why: Pre-execution sensitivity analysis for slippage and flash crashes.
  - *Strategic Importance:* 8.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium (Requires rare-event simulator integration)
  - *Operational Leverage:* Medium (Improves trust in high-lot signals)
  - *End-user/Operator Value:* Rehearses trade outcomes before committing capital.

- **Trade Narrative Memory (LLM-Enhanced)** — Score: 7.5/10 | Cost: L | Why: Qualitative "Why?" analysis for every trade using LLM synthesis.
  - *Strategic Importance:* 7.0/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium (Requires LLM API integration)
  - *Operational Leverage:* Low (Long-term alpha refinement)
  - *End-user/Operator Value:* Automates qualitative trade journaling and alpha discovery.

- **Institutional Gold Flow & Physical Demand Proxies** — Score: 7.2/10 | Cost: M | Why: Track physical gold market dynamics (ETF flows, SGE premiums) to detect divergences between paper and physical markets.
  - *Strategic Importance:* 7/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High
  - *Operational Leverage:* Medium
  - *End-user/Operator Value:* Provides a "Physical Floor" analysis to filter out speculative traps.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

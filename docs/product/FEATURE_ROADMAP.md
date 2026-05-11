# 🗺️ Strategic Feature Roadmap - May 10, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest maturity assessment and identifies high-value opportunities to eliminate operational friction and "Macro Blindness."

---

## 📊 Repo Maturity Assessment (May 10, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 7.5/10 | **Status:** Unified `RiskManager` architecture provides a solid institutional foundation. **Gap:** Missing high-fidelity slippage feedback loop and real-time capital preservation modes. |
| **Usability** | 🟢 7/10 | **Status:** Decision Cockpit TUI is highly functional for local operators. **Gap:** Still terminal-bound; lacks remote/mobile interactivity for signal approval and status monitoring. |
| **Safety** | 🟢 8.5/10 | **Status:** Circuit breakers and audited risk logging are industry-leading. **Gap:** `make emergency-stop` remains a stub; needs automated "Flatten & Fence" implementation. |
| **Intelligence** | 🟡 6.5/10 | **Status:** Regime detection is vectorized and integrated. **Gap:** "Macro Blind" to US Real Yields and DXY in the live execution loop; missing temporal model confidence heatmaps. |
| **Market Differentiation** | 🟢 8/10 | **Status:** "Glass Box" transparency sets us apart. **Gap:** Gold-specific macro overlays and LLM-enhanced trade narratives are not yet active. |

---

## High Priority (Next 2 Weeks)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 10/10 | Cost: M | Why: XAUUSD is fundamentally driven by US Real Yields and DXY. Vetoing technical signals that conflict with macro reality is the highest-value intelligence upgrade.
  - *Strategic Importance:* 10/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`src/data/event_intelligence.py` exists)
  - *Operational Leverage:* Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - *End-user/Operator Value:* Solves the primary pain of "Technical-only" blindness during Fed pivots.

- **Production-Grade Emergency Kill Switch** — Score: 9.5/10 | Cost: S | Why: Currently a stub (`make emergency-stop`). Implementing "Flatten & Fence" (close all, cancel all, lock accounts) is critical for institutional safety and rapid incident response.
  - *Strategic Importance:* 9/10
  - *Implementation Cost:* S
  - *Dependency Readiness:* 🟢 High (API hooks available in MT5/MetaAPI)
  - *Operational Leverage:* High (Foundational for capital preservation)
  - *End-user/Operator Value:* Peace of mind during catastrophic market events or system failures.

- **Telegram Interactive Command Center** — Score: 9.0/10 | Cost: M | Why: Port the Decision Cockpit to Telegram with "Approve/Reject" buttons. Transforms the bot into a mobile-accessible command center.
  - *Strategic Importance:* 9/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium
  - *Operational Leverage:* High (Increases operator mobility and response time)
  - *End-user/Operator Value:* Eliminates the need for 24/7 terminal monitoring.

## Medium Priority (Weeks 3-4)

- **Institutional What-If Execution Simulator** — Score: 8.5/10 | Cost: M | Why: Pre-execution sensitivity analysis (slippage, flash crash) allows operators to visualize potential outcomes before committing capital.
  - *Strategic Importance:* 8/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium
  - *Operational Leverage:* Medium
  - *End-user/Operator Value:* Transforms "guesswork" into rehearsed execution; increases trust in high-lot-size signals.

- **Adaptive Position Sizing (Regime Stability)** — Score: 8.2/10 | Cost: M | Why: Scale lot sizes based on the persistence and confidence of the market regime. Leans in during stable trends and steps back during fragile transitions.
  - *Strategic Importance:* 8/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`RegimeDetector` stability scores exist)
  - *Operational Leverage:* High (Optimizes capital efficiency across market cycles)
  - *End-user/Operator Value:* Automates the "risk-down" phase during regime exhaustion.

## Future Consideration

- **Trade Narrative Memory (LLM-Enhanced)** — Score: 7.5/10 | Cost: L | Why: Use an LLM to synthesize trade data into natural language post-mortems. Automates qualitative alpha discovery and trade journaling.
  - *Strategic Importance:* 7/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium
  - *Operational Leverage:* Low (Long-term alpha refinement)
  - *End-user/Operator Value:* Automates the qualitative "Why?" analysis for every trade.

- **Institutional Gold Flow & Physical Demand Proxies** — Score: 7.2/10 | Cost: M | Why: Track physical gold market dynamics (ETF flows, SGE premiums) to detect divergences between paper and physical markets.
  - *Strategic Importance:* 7/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High
  - *Operational Leverage:* Medium
  - *End-user/Operator Value:* Provides a "Physical Floor" analysis to filter out speculative traps.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

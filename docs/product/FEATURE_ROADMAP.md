# 🗺️ Strategic Feature Roadmap - May 15, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest maturity assessment and the 13-area anti-friction strategy.

---

## 📊 Repo Maturity Assessment (May 15, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟡 8.0/10 | **Status:** High-throughput execution loop (P50=1.38ms) is verified. **Gap:** Architectural regression in `main` (commit `b8c463e`) has temporarily reverted `RiskManager` to a legacy 6-layer implementation; re-harmonization with the 8-layer cascade (commit `e23adfa`) is the immediate priority. |
| **Usability** | 🟢 7.8/10 | **Status:** Decision Cockpit TUI is active. `TradeLogger` provides high-fidelity persistence. **Gap:** Telegram Interactive Gateway lacks signal approval flow ("Approve/Reject"). |
| **Safety** | 🟢 8.7/10 | **Status:** AuditedRiskManager and circuit breakers are structurally enforced. **Gap:** "Flatten & Fence" (Emergency Kill Switch) remains a verified stub in the Makefile/scripts. |
| **Intelligence** | 🟢 7.5/10 | **Status:** Regime stability scoring and WFO framework are live. **Gap:** `main.py` live loop still uses stubs for real-time Macro Risk (FRED/YFinance). |
| **Market Differentiation** | 🟢 8.8/10 | **Status:** "Glass Box" transparency and signal attribution are repo-wide standards. **Gap:** Gold-specific fractal efficiency (Hurst Exponent) and sentiment data feeds are defined but not yet implemented. |

---

## 🚀 High Priority (Next 2 Weeks)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 9.8/10 | Cost: M | Why: XAUUSD is fundamentally driven by US Real Yields and DXY.
  - *Strategic Importance:* 10/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`src/data/event_intelligence.py` logic is mature)
  - *Operational Leverage:* Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - *End-user Value:* Solves fundamental blindness during Fed pivots and news-driven spikes.

- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.6/10 | Cost: S | Why: Currently a Makefile stub.
  - *Strategic Importance:* 9.8/10
  - *Implementation Cost:* S
  - *Dependency Readiness:* 🟢 High (MT5 connector supports position management)
  - *Operational Leverage:* High (Foundational for capital preservation and compliance)
  - *End-user Value:* Instant capital protection during catastrophic market/system events.

- **Telegram Interactive Command Center (Human-in-the-Loop)** — Score: 9.3/10 | Cost: M | Why: Port the Decision Cockpit to Telegram with "Approve/Reject" buttons.
  - *Strategic Importance:* 9.2/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟡 Medium (Requires bot gateway integration into the live loop)
  - *Operational Leverage:* High (Increases mobility and operator response time)
  - *End-user Value:* Eliminates terminal monitoring; provides secure remote control.

## ⚖️ Medium Priority (Weeks 3-4)

- **Institutional Fractal Efficiency & Regime Persistence** — Score: 9.1/10 | Cost: M | Why: Quantify market memory and trend persistence for XAUUSD.
  - *Strategic Importance:* 9.1/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (Feature 13 is already defined and scoped)
  - *Operational Leverage:* High (Mathematical edge in distinguishing trends from noise)
  - *End-user Value:* Reduces false breakout entries in efficient (random-walk) markets.

- **Institutional Sentiment & Positioning Intelligence (Alpha)** — Score: 8.8/10 | Cost: M | Why: Implement data harvesting for CFTC COT and retail sentiment ratios.
  - *Strategic Importance:* 9.0/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (Feature 12 is already defined and scoped)
  - *Operational Leverage:* High (Strong differentiation via "Crowded Trade Detection")
  - *End-user Value:* Prevents entering late-stage exhausted trends.

- **Adaptive Execution Feedback Loop (Slippage-Aware)** — Score: 8.5/10 | Cost: M | Why: Use realized slippage to dynamically adjust filter thresholds.
  - *Strategic Importance:* 8.5/10
  - *Implementation Cost:* M
  - *Dependency Readiness:* 🟢 High (`ExecutionQuality` metrics are already logged)
  - *Operational Leverage:* Medium (Optimizes fill probability in changing liquidity)
  - *End-user Value:* Automatically "backs off" during toxic liquidity or broker degradation.

## 🔭 Future Consideration

- **Institutional Gold Flow & Physical Demand Proxies** — Score: 7.8/10 | Cost: L | Why: Track ETF flows and Shanghai premiums.
  - *Strategic Importance:* 7.8/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟢 High
  - *Operational Leverage:* Medium (Divergence detection)
  - *End-user Value:* Visibility into "Smart Money" accumulation vs. retail churn.

- **Trade Narrative Memory (LLM-Enhanced)** — Score: 7.5/10 | Cost: L | Why: Qualitative "Why?" analysis for every trade using LLM synthesis.
  - *Strategic Importance:* 7.5/10
  - *Implementation Cost:* L
  - *Dependency Readiness:* 🟡 Medium (Requires LLM API integration)
  - *Operational Leverage:* Medium (Automated journaling and alpha discovery)
  - *End-user Value:* Post-trade review automation.

- **Autonomous Parameter Self-Optimization** — Score: 7.2/10 | Cost: XL | Why: Dynamic tuning of ExecutionFilter and RiskManager parameters.
  - *Strategic Importance:* 8.0/10
  - *Implementation Cost:* XL
  - *Dependency Readiness:* 🔴 Low (Requires significant research)
  - *Operational Leverage:* High (Full autonomy)
  - *End-user Value:* Eliminates manual "tuning" of risk thresholds.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

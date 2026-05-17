# 🗺️ Strategic Feature Roadmap - May 16, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader into an institutional-grade "Glass Box" system. It reflects the latest maturity assessment and the 13-area anti-friction strategy.

---

## 📊 Repo Maturity Assessment (May 16, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟡 8.5/10 | **Status:** High-throughput execution loop (P50=1.38ms) is verified. **Gap:** Fragmentation in Risk Management—`RiskManager` still uses 6-layer logic while `RiskEngine` (harmonized) is disconnected. |
| **Usability** | 🟡 7.5/10 | **Status:** Decision Cockpit TUI is functional. **Gap:** Operator is tethered to the terminal; lacks mobile command/control and signal approval flow. |
| **Safety** | 🟢 8.8/10 | **Status:** AuditedRiskManager and circuit breakers are structurally enforced. **Gap:** Emergency "Flatten & Fence" (Emergency Kill Switch) remains a verified stub in the Makefile/scripts. |
| **Intelligence** | 🟡 7.2/10 | **Status:** Regime stability scoring and WFO framework are live. **Gap:** `main.py` live loop still uses stubs for real-time Macro Risk (FRED/YFinance). |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** "Glass Box" transparency and signal attribution are the standard. **Gap:** XAUUSD-specific fractal efficiency (Hurst Exponent) and sentiment data feeds are defined but not live. |

---

## 🚀 High Priority (Next 2 Weeks)

- **Main Alignment: Risk Management Harmonization**
  - **Score:** 10/10 | **Cost:** S | **Dependency Readiness:** 🟢 High
  - **Why:** Critical architectural debt. Consolidation of the 8-layer risk cascade into `RiskManager` to restore test integrity and safety parity.
  - **Strategic Importance:** 10/10
  - **Implementation Cost:** S
  - **Operational Leverage:** High (Restores core system truth and safety)
  - **End-user Value:** Reliable, verified institutional risk controls.

- **Production-Grade Emergency Kill Switch ("Flatten & Fence")**
  - **Score:** 9.9/10 | **Cost:** S | **Dependency Readiness:** 🟢 High
  - **Why:** Foundational capital protection. Converts the Makefile stub into a hardened, cross-platform position-liquidation service.
  - **Strategic Importance:** 10/10
  - **Implementation Cost:** S
  - **Operational Leverage:** High (Instant risk reduction across all symbols)
  - **End-user Value:** Solves the "what if it goes rogue?" fear; provides instant peace of mind.

- **Live Macro Intelligence Pipeline (FRED/YFinance)**
  - **Score:** 9.8/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** XAUUSD is fundamentally driven by US Real Yields and DXY. Eliminates blindness to fundamental pivots and news-driven spikes.
  - **Strategic Importance:** 10/10
  - **Implementation Cost:** M
  - **Operational Leverage:** Massive (Reduces drawdown by avoiding "yield-trap" breakouts)
  - **End-user Value:** Institutionalizes the AI's "vibe check" against high-fidelity macro data.

- **Telegram Interactive Command Center (Human-in-the-Loop)**
  - **Score:** 9.4/10 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
  - **Why:** Port the Decision Cockpit to Telegram with "Approve/Reject" buttons. Decouples the operator from the terminal.
  - **Strategic Importance:** 9.5/10
  - **Implementation Cost:** M
  - **Operational Leverage:** High (Increases mobility and operator response time)
  - **End-user Value:** Secure, anytime control; eliminates the need for 24/7 terminal monitoring.

## ⚖️ Medium Priority (Weeks 3-4)

- **Institutional Fractal Efficiency & Regime Persistence**
  - **Score:** 9.2/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** Uses the Hurst Exponent (H) and Fractal Dimension (D) to mathematically distinguish persistent trends from noise.
  - **Strategic Importance:** 9.2/10
  - **Implementation Cost:** M
  - **Operational Leverage:** High (Mathematical edge in timing trend entries)
  - **End-user Value:** Reduces false breakout entries in efficient (random-walk) markets.

- **Institutional Sentiment & Positioning Intelligence**
  - **Score:** 8.9/10 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
  - **Why:** Implement data harvesting for CFTC COT and retail sentiment ratios to identify "Crowded Trades".
  - **Strategic Importance:** 9.0/10
  - **Implementation Cost:** M
  - **Operational Leverage:** High (Leading indicator of structural reversals)
  - **End-user Value:** Prevents entering late-stage exhausted trends; prepares for high-conviction pivots.

- **Adaptive Execution Feedback Loop (Slippage-Aware)**
  - **Score:** 8.6/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** Use realized slippage from `TradeLogger` to dynamically adjust filter thresholds and entry logic.
  - **Strategic Importance:** 8.5/10
  - **Implementation Cost:** M
  - **Operational Leverage:** Medium (Optimizes fill probability in changing liquidity)
  - **End-user Value:** Automatically "backs off" during toxic liquidity or broker degradation.

##  Telescope Future Consideration

- **Institutional Gold Flow & Physical Demand Proxies**
  - **Score:** 7.9/10 | **Cost:** L | **Dependency Readiness:** 🟢 High
  - **Why:** Track GLD/IAU flows and Shanghai premiums to detect physical vs. paper divergences.
  - **Strategic Importance:** 8.0/10
  - **Implementation Cost:** L
  - **Operational Leverage:** Medium (Fundamental anchor for technical signals)
  - **End-user Value:** Visibility into "Smart Money" physical accumulation.

- **Trade Narrative Memory (LLM-Enhanced)**
  - **Score:** 7.6/10 | **Cost:** L | **Dependency Readiness:** 🟡 Medium
  - **Why:** Qualitative "Why?" analysis for every trade using LLM synthesis of market telemetry.
  - **Strategic Importance:** 7.5/10
  - **Implementation Cost:** L
  - **Operational Leverage:** Medium (Automated journaling and alpha discovery)
  - **End-user Value:** Post-trade review automation for institutional compliance.

- **Autonomous Parameter Self-Optimization**
  - **Score:** 7.1/10 | **Cost:** XL | **Dependency Readiness:** 🔴 Low
  - **Why:** Dynamic tuning of ExecutionFilter and RiskManager parameters via internal research loops.
  - **Strategic Importance:** 8.5/10
  - **Implementation Cost:** XL
  - **Operational Leverage:** High (Full autonomy)
  - **End-user Value:** Eliminates the need for manual "tuning" of risk thresholds.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

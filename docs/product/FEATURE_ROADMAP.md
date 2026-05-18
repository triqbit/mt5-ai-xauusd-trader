# 🗺️ Strategic Feature Roadmap - May 18, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader into an institutional-grade "Glass Box" system. It reflects the latest maturity assessment and the resolution of the "Disconnected Root" architectural crisis.

---

## 📊 Repo Maturity Assessment (May 18, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟡 8.5/10 | **Status:** High-throughput execution loop (P50=31.59ms) verified. **Gap:** History fragmentation; Harmonized 8-layer Risk API and Feature Engineering relocation are isolated in the `coherence` branch, missing from `main`. |
| **Usability** | 🟡 7.5/10 | **Status:** Decision Cockpit TUI functional. **Gap:** Operator tethered to terminal; lacks mobile command/control and interactive signal approval. |
| **Safety** | 🟢 8.8/10 | **Status:** 8-layer safety cascade defined and implemented on integration branches. **Gap:** Emergency "Flatten & Fence" (Kill Switch) remains a verified stub (`scripts/emergency_flatten.py` required). |
| **Intelligence** | 🟡 7.2/10 | **Status:** Regime stability scoring and Walk-Forward Optimization (WFO) live. **Gap:** `main.py` live loop still uses stubs for real-time Macro Risk (FRED/YFinance). |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** "Glass Box" transparency and signal attribution are the system standard. **Gap:** XAUUSD-specific metrics like Hurst Exponent and Physical Gold Flows are defined but not live. |

---

## 🚀 High Priority (Next 2 Weeks)

- **History Harmonization & Global Root Resolution**
  - **Score:** 10/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** The "Disconnected Root" crisis is the #1 strategic blocker. Merging feature branches into `main` is currently high-risk due to non-ancestral history.
  - **Strategic Importance:** 10/10 | **Operational Leverage:** Critical
  - **End-user Value:** Ensures system stability and deterministic updates.

- **Deterministic Merge Queue Implementation**
  - **Score:** 9.9/10 | **Cost:** S | **Dependency Readiness:** 🟢 High
  - **Why:** Automates the Jules05 governor role. Prioritizes #1280 (Architectural Harmonization) as the system base to resolve fragmentation.
  - **Strategic Importance:** 10/10 | **Operational Leverage:** High
  - **End-user Value:** Rapid, safe delivery of new features without regressions.

- **Production-Grade Emergency Kill Switch ("Flatten & Fence")**
  - **Score:** 9.9/10 | **Cost:** S | **Dependency Readiness:** 🟢 High
  - **Why:** Foundational capital protection. Implement `scripts/emergency_flatten.py` to reconcile local state and liquidate all positions instantly.
  - **Strategic Importance:** 10/10 | **Operational Leverage:** High
  - **End-user Value:** Provides instant peace of mind and protection against "rogue" bot behavior.

- **Main Alignment: Risk & Feature Engineering Harmonization**
  - **Score:** 9.8/10 | **Cost:** S | **Dependency Readiness:** 🟢 High
  - **Why:** Reconcile the coherence branch with `main` once history is grafted. Restores 8-layer risk integrity and standardized FE paths.
  - **Strategic Importance:** 9.5/10 | **Operational Leverage:** High
  - **End-user Value:** Reliable, verified institutional risk controls.

## ⚖️ Medium Priority (Weeks 3-4)

- **Live Macro Intelligence Pipeline (FRED/YFinance)**
  - **Score:** 9.7/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** Gold is fundamentally driven by US Real Yields and DXY. Eliminates blindness to fundamental pivots.
  - **Strategic Importance:** 9.5/10 | **Operational Leverage:** Massive
  - **End-user Value:** Reduces drawdown by avoiding "yield-trap" breakouts.

- **Telegram Interactive Command Center (Human-in-the-Loop)**
  - **Score:** 9.4/10 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
  - **Why:** Port the Decision Cockpit to Telegram with "Approve/Reject" buttons. Decouples the operator from the terminal.
  - **Strategic Importance:** 9.2/10 | **Operational Leverage:** High
  - **End-user Value:** Secure, anytime control; eliminates the need for 24/7 monitoring.

- **Institutional Fractal Efficiency & Regime Persistence**
  - **Score:** 9.2/10 | **Cost:** M | **Dependency Readiness:** 🟢 High
  - **Why:** Uses the Hurst Exponent (H) to mathematically distinguish persistent trends from noise.
  - **Strategic Importance:** 9.0/10 | **Operational Leverage:** High
  - **End-user Value:** Reduces false breakout entries in efficient (random-walk) markets.

##  Telescope Future Consideration

- **Institutional Sentiment & Positioning Intelligence (COT)**
  - **Score:** 8.9/10 | **Cost:** M | **Why:** Identification of "Crowded Trades" via CFTC COT and retail sentiment ratios.
- **Adaptive Execution Feedback Loop (Slippage-Aware)**
  - **Score:** 8.6/10 | **Cost:** M | **Why:** Use realized slippage to dynamically adjust filter thresholds.
- **Trade Narrative Memory (LLM-Enhanced)**
  - **Score:** 7.6/10 | **Cost:** L | **Why:** Qualitative "Why?" analysis for every trade using LLM synthesis of market telemetry.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

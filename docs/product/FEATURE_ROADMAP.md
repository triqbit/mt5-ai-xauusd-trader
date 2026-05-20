# 🗺️ Strategic Feature Roadmap - May 20, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader into an institutional-grade "Glass Box" system. It reflects the latest maturity assessment following the assembly of Release Candidate v1.1.0-rc10 and the identified process integrity risks.

---

## 📊 Repo Maturity Assessment (May 20, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🔴 8.5/10 | **Status:** RC v1.1.0-rc10 assembled with 173 passing tests. **Gap:** **CRITICAL:** `main` branch remains in RED status for process integrity due to history destruction. History Harmonization is the top priority. |
| **Usability** | 🟡 7.8/10 | **Status:** Decision Cockpit TUI functional; setup/config improved. **Gap:** High setup friction (TA-Lib C-dependencies) persists for new users. "One-Command" Dockerized environment is missing. |
| **Safety** | 🟢 9.0/10 | **Status:** 8-layer safety cascade integrated. **Gap:** Emergency "Flatten & Fence" (Kill Switch) implementation needs to be verified on the main branch. Missing "Hardened Mode Gate" for live/demo safety. |
| **Intelligence** | 🟡 7.2/10 | **Status:** Regime Detector and Calibration Engine integrated. **Gap:** Real-time Macro Risk (FRED/YFinance) remains a simulation. Alpha discovery is manual. |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** Signal Attribution and WFO are standards. **Gap:** XAUUSD-specific metrics like Hurst Exponent and Physical Gold Flows are defined but not live. |

---

## High Priority (Next 2 Weeks)
- **History Harmonization & Global Root Resolution** — Score: 10/10 | Cost: M | Why: Resolves the "Disconnected Root" crisis which is the primary blocker for all feature delivery. Restore forensic traceability and enables safe branch integration. (Ready: 🟢, Leverage: Critical, Value: Deterministic Updates)
- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.9/10 | Cost: S | Why: Implementation of `scripts/emergency_flatten.py` and `MT5Connector.close_position` for foundational capital protection. Liquidates positions and fences the account instantly. (Ready: 🟢, Leverage: High, Value: Peace of Mind)
- **One-Command Dev Environment (Dockerization)** — Score: 9.2/10 | Cost: M | Why: Eliminates 45+ minutes of setup friction and TA-Lib compilation failures by standardizing the environment for all contributors. (Ready: 🟢, Leverage: High, Value: Developer/Agent UX)
- **Deterministic Merge Queue Implementation** — Score: 9.5/10 | Cost: S | Why: Automates the Jules05 governor role, enabling safe, high-velocity integration of intelligence and safety features. (Ready: 🟢, Leverage: High, Value: Delivery Velocity)

## Medium Priority (Weeks 3-4)
- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 9.7/10 | Cost: M | Why: Integrates US Real Yields and DXY drivers to avoid fundamental "yield-trap" breakouts in the XAUUSD market. (Ready: 🟢, Leverage: Massive, Value: Alpha & Safety)
- **Institutional Sentiment Intelligence Alpha** — Score: 9.5/10 | Cost: M | Why: Deploy Alpha pipeline for CFTC COT and retail sentiment data integration to capture crowd positioning. (Ready: 🟢, Leverage: High, Value: Market Insight)
- **Hardened Mode Gate (Account Safety)** — Score: 8.5/10 | Cost: S | Why: Verification that `trade_mode` matches environment configuration at the connector level to prevent accidental live trading. (Ready: 🟢, Leverage: Medium, Value: Catastrophe Prevention)
- **Telegram Interactive Command Center (Human-in-the-Loop)** — Score: 9.4/10 | Cost: M | Why: Ports the Decision Cockpit to Telegram with "Approve/Reject" buttons, allowing remote management without a terminal. (Ready: 🟡, Leverage: High, Value: Mobile Control)

## Future Consideration
- **Institutional Fractal Efficiency (Hurst Exponent)** — Score: 8.9/10 | Why: Mathematically distinguish persistent trends from mean-reverting noise specifically for XAUUSD market regimes.
- **Trade Narrative Memory (LLM-Enhanced Post-Mortem)** — Score: 8.1/10 | Why: Qualitative analysis of "Why did this trade happen?" using LLM synthesis of system telemetry and market context.
- **Adaptive Execution Feedback (Slippage-Aware)** — Score: 7.8/10 | Why: Uses realized slippage from `TradeLogger` to dynamically adjust execution filters and entry aggression.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

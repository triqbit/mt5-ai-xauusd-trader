# 🗺️ Strategic Feature Roadmap - May 19, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader into an institutional-grade "Glass Box" system. It reflects the latest maturity assessment following the assembly of Release Candidate v1.1.0-rc10 and the ongoing resolution of repository history fragmentation.

---

## 📊 Repo Maturity Assessment (May 19, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🔴 8.5/10 | **Status:** RC v1.1.0-rc10 assembled with 173 passing tests. **Gap:** **CRITICAL:** `main` branch (commit `ea16529f`) is in RED status for process integrity due to history destruction. Architectural Harmonization (#1280) is the required base. |
| **Usability** | 🟡 7.5/10 | **Status:** Decision Cockpit TUI functional. **Gap:** High setup friction (TA-Lib C-dependencies). Missing "One-Command" Dockerized development environment. |
| **Safety** | 🟢 8.8/10 | **Status:** 8-layer safety cascade fully integrated. **Gap:** Emergency "Flatten & Fence" (Kill Switch) remains a verified stub (`scripts/emergency_flatten.py`). Missing "Hardened Mode Gate" to prevent Real account trading in Demo mode. |
| **Intelligence** | 🟡 7.2/10 | **Status:** Regime Detector and Confidence Calibration Engines integrated into RC. **Gap:** Real-time Macro Risk (FRED/YFinance) remains a simulation. Alpha discovery is currently a manual process. |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** "Glass Box" transparency, Signal Attribution, and WFO are system standards. **Gap:** XAUUSD-specific metrics like Hurst Exponent and Physical Gold Flows are defined but not live in the core loop. |

---

## High Priority (Next 2 Weeks)
- **History Harmonization & Global Root Resolution** — Score: 10/10 | Cost: M | Why: Resolves the "Disconnected Root" crisis which is the primary blocker for all feature delivery. Restore forensic traceability and enables safe branch integration. (Ready: 🟢, Leverage: Critical, Value: Deterministic Updates)
- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.9/10 | Cost: S | Why: Implementation of `scripts/emergency_flatten.py` for foundational capital protection. Liquidates positions and fences the account instantly. (Ready: 🟢, Leverage: High, Value: Peace of Mind)
- **One-Command Dev Environment (Dockerization)** — Score: 9.2/10 | Cost: M | Why: Eliminates 45+ minutes of setup friction and TA-Lib compilation failures by standardizing the environment for all contributors. (Ready: 🟢, Leverage: High, Value: Developer/Agent UX)
- **Deterministic Merge Queue Implementation** — Score: 9.5/10 | Cost: S | Why: Automates the Jules05 governor role, enabling safe, high-velocity integration of intelligence and safety features. (Ready: 🟢, Leverage: High, Value: Delivery Velocity)

## Medium Priority (Weeks 3-4)
- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 9.7/10 | Cost: M | Why: Integrates US Real Yields and DXY drivers to avoid fundamental "yield-trap" breakouts in the XAUUSD market. (Ready: 🟢, Leverage: Massive, Value: Alpha & Safety)
- **Telegram Interactive Command Center (Human-in-the-Loop)** — Score: 9.4/10 | Cost: M | Why: Ports the Decision Cockpit to Telegram with "Approve/Reject" buttons, allowing remote management without a terminal. (Ready: 🟡, Leverage: High, Value: Mobile Control)
- **Hardened Mode Gate (Account Safety)** — Score: 8.5/10 | Cost: S | Why: Verification that `trade_mode` matches environment configuration at the connector level to prevent accidental live trading. (Ready: 🟢, Leverage: Medium, Value: Catastrophe Prevention)

## Future Consideration
- **Institutional Fractal Efficiency (Hurst Exponent)** — Score: 8.9/10 | Why: Mathematically distinguish persistent trends from mean-reverting noise specifically for XAUUSD market regimes.
- **Trade Narrative Memory (LLM-Enhanced Post-Mortem)** — Score: 8.1/10 | Why: Qualitative analysis of "Why did this trade happen?" using LLM synthesis of system telemetry and market context.
- **Adaptive Execution Feedback (Slippage-Aware)** — Score: 7.8/10 | Why: Uses realized slippage from `TradeLogger` to dynamically adjust execution filters and entry aggression.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

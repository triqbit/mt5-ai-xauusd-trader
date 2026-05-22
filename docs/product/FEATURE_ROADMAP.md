# 🗺️ Strategic Feature Roadmap - May 22, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader into an institutional-grade "Glass Box" system. It reflects the latest maturity assessment and identifies the critical path for resolving process integrity, safety gaps, and technical drift.

---

## 📊 Repo Maturity Assessment (May 22, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🔴 8.5/10 | **Status:** RC v1.1.0-rc10 verified; 173 passing tests. **Gap:** **CRITICAL:** 25th consecutive day of history destruction recorded. Forensic traceability is lost. |
| **Usability** | 🟡 7.8/10 | **Status:** Decision Cockpit TUI functional. **Gap:** High setup friction (TA-Lib C-dependencies). "One-Command" Dockerized environment is proposed but missing. |
| **Safety** | 🔴 8.5/10 | **Status:** 8-layer safety logic defined. **Gap:** **HIGH RISK:** "Risk API Drift" persists—`main.py` uses legacy `approve()` while harmonized tests fail. Emergency Kill Switch is missing. |
| **Intelligence** | 🟢 9.6/10 | **Status:** Regime Detector and Calibration Engine are live. **Gap:** Real-time Macro Risk (FRED/YFinance) remains in simulation mode. |
| **Market Differentiation** | 🟢 8.5/10 | **Status:** Signal Attribution and WFO are standards. **Gap:** XAUUSD-specific metrics like Hurst Exponent and Physical Gold Flows are in research/acceptance phase. |

---

## High Priority (Next 2 Weeks)

- **Risk API Harmonization (Drift Resolution)** — Score: 10/10 | Cost: S | Why: Resolves the 100% failure rate in harmonized risk tests. Aligns `RiskManager.approve()` with `validate_signal()` and integrates ATR-based sizing. (Ready: 🟢, Leverage: High, Value: Safety Integrity)
- **History Harmonization & Global Root Resolution** — Score: 10/10 | Cost: M | Why: Resolves the "Disconnected Root" crisis. Restores forensic traceability and enables safe branch integration for all agents. (Ready: 🟢, Leverage: Critical, Value: Deterministic Updates)
- **Production-Grade Emergency Kill Switch ("Flatten & Fence")** — Score: 9.9/10 | Cost: S | Why: Implementation of `scripts/emergency_flatten.py` and `MT5Connector.close_position` for foundational capital protection. (Ready: 🟢, Leverage: High, Value: Peace of Mind)
- **One-Command Dev Environment (Dockerization)** — Score: 9.2/10 | Cost: M | Why: Eliminates 45+ minutes of setup friction and TA-Lib compilation failures by standardizing the environment. (Ready: 🟢, Leverage: High, Value: Developer UX)
- **Deterministic Merge Queue & CI Gates** — Score: 9.5/10 | Cost: S | Why: Automates the Jules05 governor role, enforcing history integrity and API compatibility checks before merge. (Ready: 🟢, Leverage: High, Value: Delivery Velocity)

## Medium Priority (Weeks 3-4)

- **Live Macro Intelligence Pipeline (FRED/YFinance)** — Score: 9.7/10 | Cost: M | Why: Integrates US Real Yields and DXY drivers to avoid fundamental "yield-trap" breakouts in XAUUSD. (Ready: 🟢, Leverage: Massive, Value: Alpha & Safety)
- **Institutional Gold Flow & Physical Demand Proxies** — Score: 9.5/10 | Cost: M | Why: Incorporates GLD/IAU flows and SGE premiums to distinguish physical demand from paper-market noise. (Ready: 🟢, Leverage: High, Value: XAUUSD Edge)
- **Telegram Interactive Command Center** — Score: 9.4/10 | Cost: M | Why: Ports Decision Cockpit to Telegram with "Approve/Reject" buttons for remote management. (Ready: 🟡, Leverage: High, Value: Mobile Control)
- **Hardened Mode Gate (Account Safety)** — Score: 8.5/10 | Cost: S | Why: Prevents accidental live trading by verifying `trade_mode` against environment config at the connector level. (Ready: 🟢, Leverage: Medium, Value: Catastrophe Prevention)

## Future Consideration

- **Institutional Fractal Efficiency (Hurst Exponent)** — Score: 8.9/10 | Why: Mathematically distinguish persistent trends from mean-reverting noise specifically for XAUUSD.
- **Trade Narrative Memory (LLM-Enhanced Post-Mortem)** — Score: 8.1/10 | Why: Qualitative analysis of "Why did this trade happen?" using LLM synthesis of telemetry.
- **Adaptive Execution Feedback (Slippage-Aware)** — Score: 7.8/10 | Why: Uses realized slippage from `TradeLogger` to dynamically adjust execution filters.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

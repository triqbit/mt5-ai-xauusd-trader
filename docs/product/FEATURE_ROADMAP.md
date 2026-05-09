# 🗺️ Strategic Feature Roadmap - May 9, 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system. It reflects the latest architectural consolidation of the Risk Management core.

---

## 📊 Repo Maturity Assessment (May 9, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 7.5/10 | **Status:** Unified `RiskManager` architecture provides a solid institutional foundation. Kelly-based sizing and ATR-scaled SL/TP are production-ready. **Gap:** Missing high-fidelity slippage feedback loop and real-time capital preservation modes. |
| **Usability** | 🟢 7/10 | **Status:** Decision Cockpit TUI is highly functional for local operators. `Makefile` one-command workflows are robust. **Gap:** Still terminal-bound; lacks remote/mobile interactivity for signal approval. |
| **Safety** | 🟢 8.5/10 | **Status:** Circuit breakers, health gates, and audited risk logging are industry-leading. Temporal standardization is complete. **Gap:** `make emergency-stop` remains a stub; needs automated "Flatten & Fence" implementation. |
| **Intelligence** | 🟡 6.5/10 | **Status:** Regime detection is vectorized and integrated. Ensemble consensus is live. **Gap:** "Macro Blind" to US Real Yields and DXY in the live execution loop; missing temporal model confidence heatmaps. |
| **Differentiation** | 🟢 8/10 | **Status:** "Glass Box" transparency sets us apart from retail bots. XAUUSD-specific risk scaling is highly tuned. **Gap:** Gold-specific macro overlays and LLM-enhanced trade narratives are not yet active. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Live Macro Intelligence Pipeline (FRED/YFinance)
- **Score:** 10/10 | **Cost:** M | **Rationale:** XAUUSD is fundamentally driven by US Real Yields and the Dollar Index (DXY). Vetoing technical signals that conflict with macro reality is the highest-value intelligence upgrade.
- **Strategic Importance:** 10 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High (`src/data/event_intelligence.py` exists)
- **Operational Leverage:** Massive | **End-user Value:** 10
- **Pain Solved:** Prevents "technical-only" signal traps during hawkish Fed pivots or yield spikes.

### 2. Production-Grade Emergency Kill Switch (Flatten & Fence)
- **Score:** 9.5/10 | **Cost:** S | **Rationale:** Transition the `make emergency-stop` stub into a production utility that immediately closes all positions and cancels pending orders across all connected accounts.
- **Strategic Importance:** 9 | **Implementation Cost:** S | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** High | **End-user Value:** 10 (Safety)
- **Pain Solved:** Provides a "Big Red Button" for catastrophic market events or system failures.

### 3. Autonomous Governance & Auto-Merge Scaling
- **Score:** 9.0/10 | **Cost:** S | **Rationale:** The ~400 PR backlog is the primary operational friction. Expanding deterministic auto-merge rules for "Safe Surface" and "Technical Debt" categories is critical for velocity.
- **Strategic Importance:** 9 | **Implementation Cost:** S | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Massive | **End-user Value:** 8
- **Pain Solved:** Eliminates manual triage bottlenecks and reduces stale PR turbulence.

---

## 📈 Medium Priority (Weeks 3-4)

### 4. Adaptive Position Sizing Based on Regime Stability
- **Score:** 9.2/10 | **Cost:** M | **Rationale:** Dynamically scale lot sizes based on the persistence and confidence of the market regime. Leans in during stable trends and reduces exposure in fragile/transitional regimes.
- **Strategic Importance:** 9 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High (`RegimeDetector` stability scores exist)
- **Operational Leverage:** High | **End-user Value:** 9
- **Pain Solved:** Prevents over-leverage in unstable market conditions and optimizes capital efficiency.

### 5. Telegram Interactive Command Center
- **Score:** 8.5/10 | **Cost:** M | **Rationale:** Port the Decision Cockpit output to Telegram with "Approve/Reject" buttons. Transforms the bot into a mobile-accessible command center.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** High | **End-user Value:** 10
- **Pain Solved:** Eliminates the need for 24/7 terminal monitoring; allows remote intervention for high-value signals.

### 6. Model Confidence Heatmaps Over Time
- **Score:** 8.0/10 | **Cost:** M | **Rationale:** Temporal stability visualization in the Cockpit. Identifies when a model's confidence is decoupling from realized accuracy across different regimes.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** High | **End-user Value:** 8
- **Pain Solved:** Detects model drift and "regime-exhaustion" before it impacts the bottom line.

---

## 🔭 Future Consideration

### 7. Adaptive Capital-Preservation Operating Modes
- **Score:** 8.2/10 | **Cost:** M | **Rationale:** Top-down risk governance (Defensive/Aggressive) that automatically pivots entire logic based on drawdown or macro event density.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** Medium | **End-user Value:** 9
- **Pain Solved:** Automates strategic risk pivoting during volatile periods (e.g., FOMC week).

### 8. Trade Narrative Memory (LLM-Enhanced)
- **Score:** 7.5/10 | **Cost:** L | **Rationale:** Use an LLM to synthesize trade data into natural language post-mortems and self-correcting strategy notes.
- **Strategic Importance:** 7 | **Implementation Cost:** L | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** Low | **End-user Value:** 8
- **Pain Solved:** Automates qualitative alpha discovery and trade journaling.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

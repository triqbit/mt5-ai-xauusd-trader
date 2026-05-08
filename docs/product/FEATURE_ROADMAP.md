# 🗺️ Strategic Feature Roadmap - May 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system.

---

## 📊 Repo Maturity Assessment (May 8, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8/10 | Core institutional features (9-layer filter, Kelly allocation) are solid. **Gap:** Missing high-fidelity slippage feedback loop and real-time capital preservation modes. |
| **Usability** | 🟢 7/10 | Decision Cockpit is excellent for local TUI. **Gap:** Remote/mobile accessibility and interactive intervention are limited; setup still requires manual steps despite Makefile improvements. |
| **Safety** | 🟢 8/10 | Circuit breakers and health gates are robust. **Gap:** Emergency "Kill Switch" is currently a stub; "What-If" stress rehearsal is research-only, not integrated into the execution loop. |
| **Intelligence** | 🟡 6/10 | Regime detection is live and vectorized. **Gap:** The system remains "Macro Blind" to US Real Yields and DXY (core gold drivers) until the FRED pipeline is active. |
| **Differentiation** | 🟢 8/10 | The "Glass Box" approach and regime-awareness provide a strong edge. **Gap:** Unique gold-specific macro overlays and LLM-enhanced trade narratives are missing. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Live Macro Intelligence Pipeline (FRED/YFinance)
- **Score:** 10/10 | **Cost:** M | **Rationale:** XAUUSD is fundamentally driven by US Real Yields and the Dollar Index (DXY). Vetoing technical signals that conflict with macro reality is the highest-value intelligence upgrade.
- **Strategic Importance:** 10 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High (Base providers in `src/data/` exist)
- **Operational Leverage:** High | **End-user Value:** 10
- **Pain Solved:** Prevents "technical-only" signal traps during major macro shifts or yield spikes.

### 2. Autonomous Governance & Auto-Merge Scaling
- **Score:** 9.5/10 | **Cost:** S | **Rationale:** The ~400 PR backlog is the primary operational friction. Expanding deterministic auto-merge rules for "Safe Surface" and "Low Risk" categories is critical for development velocity.
- **Strategic Importance:** 9 | **Implementation Cost:** S | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Massive | **End-user Value:** 8
- **Pain Solved:** Eliminates manual triage bottlenecks and reduces the stale PR turbulence.

### 3. Emergency Kill Switch & Automated Flattening
- **Score:** 9.0/10 | **Cost:** S | **Rationale:** Transition the `make emergency-stop` stub into a production-grade utility that immediately closes all positions and cancels pending orders across all accounts.
- **Strategic Importance:** 9 | **Implementation Cost:** S | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** High | **End-user Value:** 10 (Safety)
- **Pain Solved:** Provides a "Big Red Button" for catastrophic market events or system failures.

---

## 📈 Medium Priority (Weeks 3-4)

### 4. Runtime "What-If" Sensitivity Panel
- **Score:** 9.2/10 | **Cost:** M | **Rationale:** Integrates research-stage stress testing into the Decision Cockpit. Visualizes the "Worst-Case Scenario" (slippage + flash reversal) before execution.
- **Strategic Importance:** 9 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium (Requires integration of `rare_event_simulator.py`)
- **Operational Leverage:** Medium | **End-user Value:** 9
- **Pain Solved:** Provides a pre-trade rehearsal of the signal's life cycle, reducing operator anxiety.

### 5. Adaptive Position Sizing Based on Regime Stability
- **Score:** 8.5/10 | **Cost:** M | **Rationale:** Dynamically scale lot sizes based on the persistence and confidence of the market regime. Leans in during stable trends and reduces exposure in fragile/transitional regimes.
- **Strategic Importance:** 9 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High (Regime Detector already provides stability scores)
- **Operational Leverage:** High | **End-user Value:** 9
- **Pain Solved:** Prevents over-leverage in unstable market conditions and optimizes capital efficiency.

### 6. Model Confidence Heatmaps Over Time
- **Score:** 8.0/10 | **Cost:** M | **Rationale:** Temporal stability visualization in the Cockpit. Identifies when a model's confidence is decoupling from realized accuracy across different regimes.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** High | **End-user Value:** 8
- **Pain Solved:** Detects model drift and "regime-exhaustion" before it impacts the bottom line.

### 7. Telegram Interactive Command Center
- **Score:** 8.0/10 | **Cost:** M | **Rationale:** Port the Decision Cockpit output to Telegram with "Approve/Reject" buttons. Transforms the bot into a mobile-accessible command center.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** High | **End-user Value:** 10
- **Pain Solved:** Eliminates the need for 24/7 terminal monitoring; allows remote intervention for high-value signals.

---

## 🔭 Future Consideration

### 8. Adaptive Execution Feedback (Slippage-Aware Filters)
- **Score:** 8.2/10 | **Cost:** M | **Rationale:** Feed realized slippage metrics back into the execution cascade. Automatically tightens entry gates if liquidity thins.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** Medium | **End-user Value:** 8
- **Pain Solved:** Prevents "Death by a Thousand Cuts" (slippage decay) in low-liquidity sessions.

### 9. LLM-Enhanced Trade Narrative Memory
- **Score:** 7.8/10 | **Cost:** L | **Rationale:** Use an LLM to synthesize trade data into natural language post-mortems and self-correcting strategy notes.
- **Strategic Importance:** 7 | **Implementation Cost:** L | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** Low | **End-user Value:** 8
- **Pain Solved:** Automates qualitative alpha discovery and trade journaling.

---
*Roadmap curated by Jules05 — Autonomous Product Steward.*

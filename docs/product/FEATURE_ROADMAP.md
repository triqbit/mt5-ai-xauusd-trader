# 🗺️ Strategic Feature Roadmap - May 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system.

---

## 📊 Repo Maturity Assessment (May 6, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8/10 | Core institutional features (9-layer filter, Kelly allocation) are solid. Gap: Missing deep-liquidity awareness and high-fidelity slippage feedback. |
| **Usability** | 🟢 7/10 | Decision Cockpit is excellent for local TUI. Gap: Remote/mobile accessibility and interactive intervention are limited. |
| **Safety** | 🟢 9/10 | Circuit breakers and health gates are robust. Gap: Pre-trade stress rehearsal is research-only, not yet in the live execution loop. |
| **Intelligence** | 🟡 6/10 | Regime detection is live but "Macro Blind" to US Real Yields and DXY, which are core gold drivers. |
| **Differentiation** | 🟢 8/10 | The "Glass Box" approach is unique. Gap: LLM-enhanced trade narrative memory to capture qualitative alpha. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Live Macro Intelligence Pipeline (FRED/YFinance)
- **Score:** 10/10 | **Cost:** M | **Why:** XAUUSD is fundamentally driven by US Real Yields and the Dollar Index (DXY). Vetoing technical signals that conflict with macro reality is the highest-value intelligence upgrade.
- **Strategic Importance:** 10 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** High | **End-user Value:** 10
- **Pain Solved:** Prevents "technical-only" signal traps during major macro shifts or yield spikes.

### 2. Autonomous Governance & Auto-Merge Scaling
- **Score:** 9.5/10 | **Cost:** S | **Why:** The ~400 PR backlog is the primary operational friction. Expanding deterministic auto-merge rules for "Safe Surface" and "Low Risk" categories is critical for development velocity.
- **Strategic Importance:** 9 | **Implementation Cost:** S | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Massive | **End-user Value:** 8
- **Pain Solved:** Eliminates manual triage bottlenecks and reduces the stale PR turbulence post-graft.

---

## 📈 Medium Priority (Weeks 3-4)

### 3. Runtime "What-If" Sensitivity Panel
- **Score:** 9.2/10 | **Cost:** M | **Why:** Integrates StressLab into the Decision Cockpit. Visualizes the "Worst-Case Scenario" (slippage + flash reversal) in the Cockpit before execution.
- **Strategic Importance:** 9 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Medium | **End-user Value:** 9
- **Pain Solved:** Provides a pre-trade rehearsal of the signal's life cycle, reducing operator anxiety.

### 4. Telegram Interactive Command Center
- **Score:** 8.8/10 | **Cost:** S | **Why:** Port the Decision Cockpit output to Telegram with "Approve/Reject" interactivity. Transforms the bot from a CLI tool into a mobile-accessible command center.
- **Strategic Importance:** 8 | **Implementation Cost:** S | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** High | **End-user Value:** 10
- **Pain Solved:** Eliminates the need for 24/7 terminal monitoring; allows remote intervention for high-value signals.

---

## 🔭 Future Consideration

### 5. Adaptive Execution Feedback (Slippage-Aware Filters)
- **Score:** 8.2/10 | **Cost:** M | **Why:** Feed realized slippage metrics back into the execution cascade. Automatically tightens entry gates if liquidity thins.
- **Strategic Importance:** 8 | **Implementation Cost:** M | **Dependency Readiness:** 🟢 High
- **Operational Leverage:** Medium | **End-user Value:** 8
- **Pain Solved:** Prevents "Death by a Thousand Cuts" (slippage decay) in low-liquidity sessions.

### 6. LLM-Enhanced Trade Narrative Memory
- **Score:** 7.8/10 | **Cost:** M | **Why:** Use an LLM to synthesize trade data into natural language post-mortems and self-correcting strategy notes.
- **Strategic Importance:** 7 | **Implementation Cost:** M | **Dependency Readiness:** 🟡 Medium
- **Operational Leverage:** Low | **End-user Value:** 8
- **Pain Solved:** Automates qualitative alpha discovery and trade journaling.

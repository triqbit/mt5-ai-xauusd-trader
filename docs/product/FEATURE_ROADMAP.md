# 🗺️ Strategic Feature Roadmap - May 2026 (Updated)

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly autonomous institutional-grade "Glass Box" trading system.

---

## 📊 Repo Maturity Assessment (May 5, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8/10 | Institutional core merged. 9-layer `ExecutionFilter`, 140+ indicator pipeline, and Kelly-based capital allocation are fully operational. |
| **Usability** | 🟢 7/10 | The `DecisionSupportSystem` (Cockpit) provides high TUI transparency. Complexity remains in remote management and mobile oversight. |
| **Safety** | 🟢 9/10 | Robust risk gates, 9-layer filtering, and Enterprise Health Gate are operational. Hardened against technical failures and connection drift. |
| **Intelligence** | 🟡 6/10 | Regime detection is live. Primary gap remains "Macro Blindness"—the system lacks real-time awareness of real yields and DXY drivers. |
| **Differentiation** | 🟢 8/10 | The "Decision Cockpit" and 9-layer filter provide institutional rigor. Next-level alpha comes from macro-alignment and predictive stress-testing. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Live Macro Intelligence Pipeline (FRED/YFinance Integration)
*   **Rationale:** Gold (XAUUSD) is fundamentally driven by US Real Yields and the Dollar Index (DXY). Integrating these external streams allows the system to veto technical signals that diverge from macro fundamentals.
*   **Score:** 10/10
*   **Strategic Importance:** 10 | **Cost:** M | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** High | **End-User Value:** 10
*   **Pain Solved:** Prevents "technical-only" signal traps during major macro shifts or yield spikes.

### 2. Autonomous Governance & Auto-Merge Expansion
*   **Rationale:** The 382 PR backlog is the primary operational friction. Expanding deterministic auto-merge rules for "Safe Surface" and "Low Risk" categories will dramatically increase development velocity.
*   **Score:** 9.5/10
*   **Strategic Importance:** 9 | **Cost:** S | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** Massive | **End-User Value:** 8
*   **Pain Solved:** Eliminates manual triage bottlenecks and reduces the 300+ stale PR turbulence.

---

## 📈 Medium Priority (Weeks 3-4)

### 3. Runtime "What-If" Sensitivity Panel
*   **Rationale:** Leverage `StressLab` to perform micro-simulations within 300ms of signal generation. Visualizes the "Worst-Case Scenario" (slippage + flash reversal) in the Cockpit before execution.
*   **Score:** 9.0/10
*   **Strategic Importance:** 9 | **Cost:** M | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** Medium | **End-User Value:** 9
*   **Pain Solved:** Provides a pre-trade rehearsal of the signal's life cycle, reducing operator anxiety.

### 4. Telegram Interactive Command Center
*   **Rationale:** Port the Decision Cockpit output to Telegram with "Approve/Reject" interactivity. Transforms the bot from a CLI tool into a mobile-accessible institutional command center.
*   **Score:** 8.5/10
*   **Strategic Importance:** 8 | **Cost:** S | **Dependency Readiness:** 🟡 Medium
*   **Operational Leverage:** High | **End-User Value:** 10
*   **Pain Solved:** Eliminates the need for 24/7 terminal monitoring; allows remote intervention for high-value signals.

---

## 🔭 Future Consideration

### 5. Adaptive Execution Feedback (Slippage-Aware Filters)
*   **Rationale:** Feed realized slippage metrics back into the execution cascade. Automatically tightens entry gates if liquidity thins.
*   **Score:** 8.0/10
*   **Strategic Importance:** 8 | **Cost:** M | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** Medium | **End-User Value:** 8
*   **Pain Solved:** Prevents "Death by a Thousand Cuts" (slippage decay) in low-liquidity sessions.

### 6. LLM-Enhanced Trade Narrative Memory
*   **Rationale:** Use an LLM to synthesize trade data into natural language post-mortems and self-correcting strategy notes.
*   **Score:** 7.5/10
*   **Strategic Importance:** 7 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
*   **Operational Leverage:** Low | **End-User Value:** 8
*   **Pain Solved:** Automates qualitative alpha discovery and trade journaling.

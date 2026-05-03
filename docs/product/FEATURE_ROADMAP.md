# 🗺️ Strategic Feature Roadmap - May 2026 (Updated)

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly institutional-grade "Glass Box" trading system.

---

## 📊 Repo Maturity Assessment (May 3, 2026)

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 8/10 | Core execution, `EnsembleModel`, `RegimeDetector`, and 6-layer `ExecutionFilter` are fully integrated into the `main.py` live loop. The system is mechanically sound. |
| **Usability** | 🟡 4/10 | The `DecisionSupportSystem` (Cockpit) provides excellent TUI transparency, but delivery is localized to the terminal. Lacks remote interactivity or push-based alerts. |
| **Safety** | 🟢 9/10 | Robust risk gates, circuit breakers, and Enterprise Health Gate are operational. The system is hardened against technical and connection failures. |
| **Intelligence** | 🟡 6/10 | High technical intelligence (LSTM/Ensemble). Primary gap is "Macro Blindness"—the system lacks real-time awareness of Gold-specific fundamental drivers (Yields/DXY). |
| **Differentiation** | 🟢 7/10 | The "Decision Cockpit" is a unique institutional feature. Next-level differentiation requires moving from passive observation to predictive stress-testing. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Live Macro Intelligence Pipeline (FRED/YFinance Integration)
*   **Rationale:** Gold (XAUUSD) is fundamentally driven by US Real Yields and the Dollar Index (DXY). Integrating these external streams into the `EventIntelligence` and `DecisionSupportSystem` allows the bot to scale down risk during violent macro shifts.
*   **Score:** 9.8/10
*   **Strategic Importance:** 10 | **Cost:** M | **Dependency Readiness:** 🟢 High (yfinance ready)
*   **Operational Leverage:** High | **End-User Value:** 10
*   **Pain Solved:** Prevents "technical-only" signal traps during major macro news or yield spikes that technical indicators cannot see.

### 2. Runtime "What-If" Sensitivity Panel (Integrated Stress-Testing)
*   **Rationale:** Leverage the `StressLab` logic to perform a micro-simulation within 300ms of signal generation. Displays the "Worst-Case Scenario" (slippage + reversal) in the Decision Cockpit before execution.
*   **Score:** 9.2/10
*   **Strategic Importance:** 9 | **Cost:** M | **Dependency Readiness:** 🟢 High (`StressLab` built)
*   **Operational Leverage:** Medium | **End-User Value:** 9
*   **Pain Solved:** Solves operator anxiety regarding "Fat Tail" events. Provides a rehearsal of the trade's life cycle before commitment.

---

## 📈 Medium Priority (Weeks 3-4)

### 3. Telegram Interactive Briefing Gate
*   **Rationale:** Port the `DecisionSupportSystem` output to Telegram with "Approve/Reject" buttons. This transforms the bot from a CLI tool into a mobile-accessible institutional command center.
*   **Score:** 8.5/10
*   **Strategic Importance:** 8 | **Cost:** S | **Dependency Readiness:** 🟡 Medium (`python-telegram-bot` needed)
*   **Operational Leverage:** High | **End-User Value:** 10
*   **Pain Solved:** Eliminates the need to monitor a terminal 24/7; allows remote intervention for high-value signals.

### 4. Adaptive Execution Feedback (Slippage-Aware Filters)
*   **Rationale:** Feed realized slippage and latency metrics from `ExecutionAnalyzer` back into the `ExecutionFilter` cascade. If XAUUSD liquidity thins, the system automatically tightens its entry gates.
*   **Score:** 8.0/10
*   **Strategic Importance:** 8 | **Cost:** M | **Dependency Readiness:** 🟢 High (`ExecutionAnalyzer` built)
*   **Operational Leverage:** Medium | **End-User Value:** 8
*   **Pain Solved:** Prevents "Death by a Thousand Cuts" (slippage decay) in low-liquidity market sessions.

---

## 🔭 Future Consideration

### 5. LLM-Enhanced Trade Narrative Memory
*   **Rationale:** Use an LLM to synthesize `trade_logger` data and "Pre-trade Briefings" into natural language post-mortems and self-correcting strategy notes.
*   **Score:** 7.2/10
*   **Strategic Importance:** 7 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
*   **Operational Leverage:** Low | **End-User Value:** 8
*   **Pain Solved:** Automated journaling and qualitative alpha discovery.

### 6. Dreamer V3 World Model Optimization
*   **Rationale:** Full transition from model-free RL to model-based RL for predictive planning in XAUUSD.
*   **Score:** 7.0/10
*   **Strategic Importance:** 7 | **Cost:** XL | **Dependency Readiness:** 🔴 Low
*   **Operational Leverage:** High (Long-term) | **End-User Value:** 6
*   **Pain Solved:** Significant increase in predictive accuracy through world-model learning.

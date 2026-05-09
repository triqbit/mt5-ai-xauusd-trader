# 🗺️ Strategic Feature Roadmap - May 2026

This roadmap defines the evolution of the MT5 AI XAUUSD Trader from a high-performance ensemble bot to a truly institutional-grade "Glass Box" trading system.

---

## 📊 Repo Maturity Assessment

| Category | Maturity | Gaps & Observations |
| :--- | :--- | :--- |
| **Product Capability** | 🟢 7/10 | Core execution and ensemble logic are solid. Key "Institutional" components (Regime/Capital Allocation) are built but not yet integrated into the live loop. |
| **Usability** | 🔴 3/10 | Pure CLI interface. Operator has low visibility into *why* decisions are made in real-time. Documentation is excellent, but UI/UX for monitoring is missing. |
| **Safety** | 🟢 8/10 | Strong risk gates, circuit breakers, and Enterprise Health Gate. Robust against hardware/connection failure. |
| **Intelligence** | 🟡 5/10 | High theoretical intelligence (Ensemble, LSTM). Lacks real-time adaptation to macro events and correlation shifts. |
| **Differentiation** | 🟡 6/10 | "Pre-trade Intelligence Briefing" is the "North Star" feature, but currently remains a design spec rather than a runtime reality. |

---

## 🚀 High Priority (Next 2 Weeks)

### 1. Institutional Intelligence Integration (The "Harmonization" Phase)
*   **Rationale:** The system has advanced components (`RegimeDetector`, `CapitalAllocator`, `DynamicEnsemble`) sitting idle in `src/`. Integrating these into `main.py` immediately elevates the bot's sophistication.
*   **Score:** 9.8/10
*   **Strategic Importance:** 10 | **Cost:** S | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** High | **End-User Value:** 9
*   **Pain Solved:** Eliminates static risk-taking; allows the bot to scale down in ranging markets and scale up in trending ones.

### 2. Explainable Regime-Aware Decision Cockpit (TUI)
*   **Rationale:** Uses `src/core/explainability.py` to provide a real-time, terminal-based dashboard (Rich-based) that shows exactly *why* a trade was taken, which model voted for it, and what the current regime context is.
*   **Score:** 9.2/10
*   **Strategic Importance:** 9 | **Cost:** M | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** Medium | **End-User Value:** 10
*   **Pain Solved:** Solves the "Black Box" anxiety. Allows operators to trust the bot by seeing its internal "thought process."

---

## 📈 Medium Priority (Weeks 3-4)

### 3. XAUUSD Macro Sensitivity Overlays (FRED/YFinance)
*   **Rationale:** Gold is driven by Real Yields, USD strength (DXY), and Geopolitics. This feature integrates these macro streams into the feature vector and risk filters.
*   **Score:** 8.5/10
*   **Strategic Importance:** 10 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
*   **Operational Leverage:** High | **End-User Value:** 8
*   **Pain Solved:** Prevents "technical-only" mistakes during major macro shifts (e.g., sudden yield spikes).

### 4. Advanced Walk-Forward Validation Lab
*   **Rationale:** Moving from static backtests to a continuous walk-forward optimization framework in `src/research/stress_lab.py`.
*   **Score:** 8.0/10
*   **Strategic Importance:** 8 | **Cost:** L | **Dependency Readiness:** 🟢 High
*   **Operational Leverage:** Medium | **End-User Value:** 7
*   **Pain Solved:** Protects against model decay and overfitting to historical Gold price action.

---

## 🔭 Future Consideration

### 5. Trade Narrative Memory (LLM-Enhanced Post-Mortem)
*   **Rationale:** Use an LLM to analyze `trade_logger` data and "Pre-trade Briefings" to generate natural language post-mortems and self-correcting strategy notes.
*   **Score:** 7.2/10
*   **Strategic Importance:** 7 | **Cost:** M | **Dependency Readiness:** 🟡 Medium
*   **Operational Leverage:** Low | **End-User Value:** 8

### 6. Dreamer V3 World Model Implementation
*   **Rationale:** Full transition from model-free RL (PPO) to model-based RL for predictive planning in XAUUSD.
*   **Score:** 7.0/10
*   **Strategic Importance:** 7 | **Cost:** XL | **Dependency Readiness:** 🔴 Low
*   **Operational Leverage:** High (Long-term) | **End-User Value:** 6

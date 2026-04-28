# Unique Institutional Features for XAUUSD AI Trading

This document defines the differentiated features that distinguish the MT5 AI/ML Trading Bot as an institutional-grade solution for Gold trading. These features are prioritized to ensure the product remains distinctive, premium, and sophisticated.

---

## 1. Explainable Regime-Aware Decision Cockpit

### What it is and why it matters
The **Explainable Regime-Aware Decision Cockpit** is a high-fidelity visualization and diagnostic interface that provides real-time transparency into the "why" behind the AI's trading decisions.

In institutional trading, "black box" models are a significant risk. Portfolio managers and risk officers need to understand the underlying logic, market regime context, and confidence levels before committing capital. This cockpit bridges the gap between complex Neural Network outputs and human-readable strategic reasoning, fostering trust and enabling better manual intervention when necessary.

### How it differentiates from generic trading bots
Most retail trading bots provide simple "Buy/Sell" signals based on basic technical indicators. Our Decision Cockpit offers:
- **Regime Contextualization:** Automatically identifies if the current XAUUSD market is in a "Mean Reversion", "Trend Following", "High Volatility Breakout", or "Liquidity Vacuum" state.
- **Model Consensus Breakdown:** Displays how different models in the ensemble (PPO, LSTM, Transformer) are voting and highlights areas of disagreement.
- **Explainable AI (XAI):** Utilizes techniques like SHAP (SHapley Additive exPlanations) or Integrated Gradients to highlight which specific features (e.g., DXY strength, real yields, or specific technical patterns) are driving the current action.
- **Institutional Confidence Scoring:** A composite score factoring in regime stability, data quality, and model agreement, providing a more nuanced view than raw probability.

### Architecture Outline
1.  **Regime Classifier:** A dedicated model component within `src/models/` that labels the current market state using historical clustering and statistical properties.
2.  **Attribution Engine:** A service that calculates feature importance in real-time for the active ensemble prediction.
3.  **Aggregation Layer:** Collects signals from the `EnsembleModel`, `RiskManager`, and `RegimeClassifier`.
4.  **Cockpit UI:** A web-based interface (e.g., using Streamlit or Dash) that polls the bot's internal state.
5.  **Telemetry API:** A lightweight internal API (e.g., FastAPI) that exposes the "thought process" data without blocking the main trading loop.

### Acceptance Criteria
- [ ] **Regime Detection:** Real-time identification and display of the current XAUUSD Market Regime.
- [ ] **Feature Attribution:** Visualization of the top 5 features contributing to the current decision.
- [ ] **Ensemble Transparency:** Comparison view showing individual model weights and votes.
- [ ] **Audit Trail:** A historical "Decision Log" that captures the full cockpit state at the moment of trade execution.
- [ ] **Performance:** Cockpit data generation must not increase the core execution loop latency by more than 50ms.

### Jules Lane Implementation
- **Jules04 (Quant Research & Institutional Innovation):** Owns the Regime Detection logic, XAI methodology, and the definition of institutional confidence metrics.
- **Jules02 (Quality & Observability):** Owns the Dashboard implementation, Telemetry API, and ensuring the system remains performant under monitoring load.

### Dependencies and Constraints
- **Dependencies:** `shap` or `captum` for explainability, `streamlit` for the UI, `fastapi` for the data bridge.
- **Constraints:** XAI calculations must be optimized (e.g., using KernelSHAP approximations) to avoid slowing down high-frequency decision windows.
- **Hardware:** May require additional memory/CPU overhead for the attribution engine.

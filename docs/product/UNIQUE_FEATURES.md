# Unique Differentiated Features

This document defines the specialized features that distinguish the MT5 AI/ML XAUUSD Trader as an institutional-grade platform.

## 1. Explainable Regime-Aware Decision Cockpit

### What it is and why it matters
The **Explainable Regime-Aware Decision Cockpit** is a sophisticated telemetry and visualization layer that provides real-time, human-readable justifications for every trading action taken by the AI.

For institutional traders, "black box" algorithms represent unacceptable operational and compliance risks. This feature bridges the gap between high-dimensional machine learning inference and human oversight by mapping model outputs to specific market regimes and weighted catalysts.

### How it differentiates from generic trading bots
Most retail bots provide binary "Buy/Sell" signals based on static indicators. This cockpit provides:
1. **Regime Identification:** Explicitly labels the current market state (e.g., "High-Volatility Trend Exhaustion" or "Asian Session Range-Bound").
2. **Logic Attribution:** Uses feature attribution (e.g., SHAP values) to show exactly which inputs (Macro yields, Technical divergences, or Order flow) drove the decision.
3. **Conviction Scoring:** Quantifies model confidence beyond a simple signal, allowing for human-in-the-loop overrides or automated size scaling.
4. **Contextual Risk Explanation:** Justifies stop-loss and take-profit placements based on current regime-specific volatility.

### Architecture Outline
- **Inference Observer:** A wrapper around `src/models` that captures internal state and feature importance during prediction.
- **Regime Classifier:** A specialized model component (managed by Jules04) that categorizes the market environment.
- **Explainability Engine:** A translation layer that maps raw feature weights to human-readable narratives.
- **Cockpit API/CLI:** Interface for retrieving the "Reasoning JSON" for live monitoring.
- **Reasoning Logger:** Extension of `src/core/trade_logger.py` to persist the decision logic for post-trade audit.

### Acceptance Criteria
- [ ] Every trade entry/exit in the database includes a `reasoning` metadata block.
- [ ] The `reasoning` block identifies at least the top 3 contributing features.
- [ ] Market regime is identified and logged for every model inference cycle.
- [ ] Integration overhead adds <15ms to the total inference-to-execution pipeline.
- [ ] Reasonings are accessible via a human-readable CLI command (e.g., `python main.py cockpit --last`).

### Implementation Lane
- **Jules04 (Quant Research):** Owns the Regime Classifier and Explainability logic.
- **Jules02 (Security & Observability):** Owns the telemetry hooks, schema validation, and API/CLI implementation.

### Dependencies and Constraints
- **Dependencies:** `shap` or `lime` for attribution; `structlog` for structured reasoning logs.
- **Constraints:** Must operate asynchronously or with minimal latency to avoid execution slippage.
- **Safety:** The cockpit is a diagnostic tool and must not have the ability to modify trade execution logic directly (separation of concerns).

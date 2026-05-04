# Acceptance Criteria: Trade Signal Explainability

## Functional Acceptance Criteria
- **Behavior:** Generate structured, human-readable, and machine-parsable explanations for why a trade signal was generated or rejected.
- **Edge Cases:**
    - Handle missing model attribution or feature data (graceful fallback to "N/A").
    - Correct mapping of model votes to `SignalDirection` (Buy/Sell/Hold).
    - Accurate identification of the "dominant" model in an ensemble.
- **Inputs/Outputs:**
    - **Inputs:** Signal direction, confidence, model votes, risk data, regime info, and feature impacts.
    - **Outputs:** `SignalExplanation` Pydantic model and terminal-formatted output (Rich/Plain).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for `SignalExplainer.explain()` logic and mapping.
    - Tests for `format_for_terminal` with and without the `rich` library.
    - Validation of the `SignalExplanation` schema.
- **Performance:**
    - Explanation generation < 50ms.
- **Error Handling:**
    - Robustness against malformed `risk_data` or `regime_info` dictionaries.
- **Observability:**
    - Log every signal explanation to a JSON-lines file for post-trade review.

## Operational Acceptance
- **Documentation:**
    - Guide for operators on interpreting the "Explainable Cockpit" TUI.
    - Description of feature cluster definitions (Trend, Volatility, etc.).
- **Configuration:**
    - Enable/disable explainability via `EXPLAINABILITY_ENABLED` env var.
- **Rollback:**
    - Non-intrusive: disabling explainability should not impact core trading logic.
- **Monitoring:**
    - Track the frequency of different rejection reasons to identify strategy bottlenecks.

## Release Readiness
- **Deployment:** Part of the "Explainable Regime-Aware Decision Cockpit" milestone.
- **Backward Compatibility:** No breaking changes to existing signals.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Product Owner.

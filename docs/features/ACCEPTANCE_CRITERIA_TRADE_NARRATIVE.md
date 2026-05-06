# Acceptance Criteria: Trade Narrative Memory

## Functional Acceptance Criteria
- **Behavior:**
    - Automatically synthesize qualitative trade "stories" combining quantitative data (regime, sentiment, signals) with life cycle analysis.
    - Captures "Why" a trade succeeded or failed (e.g., "Stop-loss hunted during low liquidity" vs. "Signal divergence from macro").
    - Provides a searchable knowledge base of market behaviors and model performance.
- **Edge Cases:**
    - Correctly handle trades that are closed due to emergency stops or manual intervention.
    - Handle scenarios with missing market context (e.g., if macro data feed was down during entry).
- **Inputs/Outputs:**
    - **Inputs:** `TradeBriefing`, `ExecutionDecision`, `TradeLogger` data, `MarketContextSnapshot`.
    - **Outputs:** `NarrativeObject` (JSON/JSONB) stored in the database, linked to `trade_id`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the Narrative Generator synthesis logic.
    - Integration tests verifying that narratives are generated within 60 seconds of trade closure.
    - Verification of linkage between narratives and historical market regimes.
- **Performance:**
    - Narrative generation should not block the main trading or logging threads.
    - Vector store search latency < 200ms for semantic retrieval.
- **Error Handling:**
    - Failures in narrative generation must be logged but should not impact trade finalization or data integrity.
- **Observability:**
    - Log "Narrative Created" events in the audit log.

## Operational Acceptance
- **Documentation:**
    - Guide on how to use the search interface for narratives.
    - Template definitions for the Narrative Generator.
- **Configuration:**
    - `NARRATIVE_GENERATION_ENABLED` (bool).
    - Optional: `LLM_API_KEY` if using LLM-enhanced synthesis.
- **Rollback:**
    - N/A (Analytical layer).
- **Monitoring:**
    - Monthly audit of narrative quality and alpha discovery utility.

## Release Readiness
- **Deployment:** Requires `TradeLogger` and `TradeBriefing` to be fully operational.
- **Backward Compatibility:** Should be able to retroactively generate narratives for historical trades if context snapshots exist.
- **Migration:** Database schema update for `trade_narratives` table.
- **Sign-off:** Requires approval from the Product Steward (Jules05).

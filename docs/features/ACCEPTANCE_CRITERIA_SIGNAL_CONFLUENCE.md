# Acceptance Criteria: Signal Confluence Metrics & Institutional Auditing

## Functional Acceptance Criteria
- **Behavior:**
    - Aggregate signals from multiple AI agents (PPO, LSTM, Dreamer) and technical overlays into a weighted "Confluence Score".
    - Track the distribution of these scores via `SIGNAL_CONFLUENCE_HISTOGRAM` to monitor signal strength clusters.
    - Provide a "Dissent Penalty" that reduces the final confluence score if high-confidence models produce opposing signals (e.g., PPO BUY vs LSTM SELL).
    - Link each confluence calculation to a specific `trace_id` for forensic auditing.
- **Edge Cases:**
    - Handle scenarios where only a subset of models is active or providing signals.
    - Gracefully handle extreme outlier signals (e.g., confidence > 1.0 or < 0.0) by clipping to boundaries.
- **Inputs/Outputs:**
    - **Inputs:** Individual `TradeSignal` objects from agents, ensemble weights.
    - **Outputs:** `WeightedConfluenceScore` (0.0-1.0), `ModelAgreementMatrix`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the `DynamicEnsembleWeighting` engine.
    - Property-based tests verifying that the confluence score remains within [0.0, 1.0] for all weight combinations.
    - Integration tests verifying `SIGNAL_CONFLUENCE_HISTOGRAM` updates in Prometheus.
- **Performance:**
    - Confluence calculation latency < 1ms.
- **Error Handling:**
    - Failure in any one model's signal generation should result in a "Neutral" (0.5) contribution from that model rather than an overall failure.
- **Observability:**
    - Visual representation of model confluence in the Decision Cockpit TUI (e.g., consensus meter).

## Operational Acceptance
- **Documentation:**
    - Technical guide on adjusting ensemble weights and consensus thresholds.
    - Documentation for the "Signal Funnel" telemetry in `docs/research/SIGNAL_AUDITING.md`.
- **Configuration:**
    - `ENSEMBLE_WEIGHTS`: JSON/Dictionary mapping model names to float weights.
    - `CONSENSUS_THRESHOLD`: Minimum confluence required to proceed to the Risk layer.
- **Rollback:**
    - Ability to switch to a single "Master Model" and bypass ensemble confluence via `USE_ENSEMBLE=FALSE`.
- **Monitoring:**
    - Alert on "Institutional Dissent" if model disagreement exceeds 80% for more than 10 iterations.

## Release Readiness
- **Deployment:** Part of the `src/models/ensemble.py` and `src/models/dynamic_ensemble.py` updates.
- **Backward Compatibility:** Must support models with legacy confidence outputs by normalizing them to [0,1].
- **Migration:** N/A.
- **Sign-off:** Requires approval from the Quant Research Lead (Jules04) and Lead Developer (Jules01).

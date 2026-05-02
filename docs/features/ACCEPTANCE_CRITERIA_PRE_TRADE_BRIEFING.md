# Acceptance Criteria: Pre-trade Intelligence Briefing

## Functional Acceptance Criteria
- **Behavior:**
    - The system must aggregate a "briefing" report immediately after a trade signal is generated but before execution.
    - The briefing must evaluate the current market context (regime, macro risk, ensemble consensus) against the signal.
    - An "Integrated Gate" must be able to block execution if the briefing risk score exceeds a configurable threshold.
- **Edge Cases:**
    - Handle timeouts in data retrieval from external macro sources (FRED/YFinance) by falling back to technical-only briefing.
    - Handle "News Shock" regimes by automatically increasing the macro risk score.
    - Gracefully handle cases where the EnsembleModel has no clear consensus (e.g., 50/50 split).
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal` object, `MarketRegime` object, `MacroMetrics` object, `EnsembleConsensus` object.
    - **Outputs:** `PreTradeBriefing` Pydantic model and a boolean `permit_execution` decision.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the briefing aggregator logic.
    - Integration tests verifying the "Integrated Gate" correctly blocks or permits orders based on briefing results.
    - Mock tests for macro data providers.
- **Performance:**
    - Briefing generation must complete in < 500ms to minimize execution latency.
- **Error Handling:**
    - If briefing generation fails due to a critical error, the system must default to a "Safe Mode" (blocking the trade).
- **Observability:**
    - Every briefing must be persisted to the `trade_briefings` table in the database.
    - Log briefing results to the system log at the `INFO` level.

## Operational Acceptance
- **Documentation:**
    - Update `OPERATIONS.md` to explain how to interpret briefing risk scores.
    - Document the `PRE_TRADE_GATE_THRESHOLD` configuration variable.
- **Configuration:**
    - `PRE_TRADE_BRIEFING_ENABLED` (bool): Master toggle for the feature.
    - `MACRO_RISK_WEIGHT` (float): Weight of macro factors in the final risk score.
- **Rollback:**
    - Disabling the briefing gate should immediately restore standard "signal-to-execution" flow.
- **Monitoring:**
    - Alert if more than 3 consecutive trades are blocked by the briefing gate (possible misconfiguration).

## Release Readiness
- **Deployment:** Can be deployed as part of the Institutional Intelligence module.
- **Backward Compatibility:** Must not break existing `TradeLogger` or `OrderManager` interfaces.
- **Migration:** Database migration required to create the `trade_briefings` table.
- **Sign-off:** Requires approval from the Quant Lead (Jules04) and Core Lead (Jules01).

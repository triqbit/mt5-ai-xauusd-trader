# Acceptance Criteria: Risk Management API Harmonization

## Functional Acceptance Criteria
- **Behavior:**
    - Consolidate disparate risk logic from `risk_engine.py` and `risk_manager.py` into a unified, thread-safe `RiskManager` API.
    - Implement the harmonized 8-layer safety cascade: Circuit Breaker, Daily Loss, Max Positions, Symbol Allocation, Minimum Confidence, Risk/Reward Ratio, Consecutive Losses, and Model Health.
    - Provide a single entry point `validate_signal(signal: TradeSignal)` that returns a detailed `RiskDecision` object.
- **Edge Cases:**
    - Handle concurrent validation requests without race conditions on account equity or position state.
    - Ensure correct risk calculation for multi-symbol portfolios (e.g., correlations between XAUUSD and other assets).
    - Gracefully handle API failures from MT5 when querying current account exposure.
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal` object, current `AccountInfo`, and `OpenPositions` list.
    - **Outputs:** `RiskDecision` containing `is_approved` (bool), `recommended_lot_size` (float), and `blocking_layer` (string, if rejected).

## Technical Acceptance
- **Test Coverage:**
    - 100% unit test coverage for the unified `RiskManager` class.
    - Property-based tests verifying that no combination of inputs can result in a lot size that exceeds the `max_risk_per_trade` limit.
- **Performance:**
    - Total validation latency for the 8-layer cascade must be < 5ms.
- **Error Handling:**
    - **Fail-Safe:** Any exception within the `RiskManager` must result in an immediate `REJECT` decision and trigger an emergency halt of the trading loop.
- **Observability:**
    - Every risk decision must be logged with `structlog` including all 8-layer scores and the final attribution.

## Operational Acceptance
- **Documentation:**
    - Detailed API reference for the unified `RiskManager` in `docs/trading/RISK_MANAGEMENT_API.md`.
    - Visualization of the 8-layer safety cascade in the feature documentation.
- **Configuration:**
    - All 8 layers must have configurable thresholds defined in `src/core/config.py`.
- **Rollback:**
    - Ability to revert to legacy `risk_engine` logic via feature flag if necessary during the transition.
- **Monitoring:**
    - Expose "Risk Rejection Rate" and "Active Blocking Layer" as Prometheus metrics.

## Release Readiness
- **Deployment:** Core trading engine update; requires coordinated restart of all bot instances.
- **Backward Compatibility:** All existing models and execution filters must be updated to use the new `validate_signal` signature.
- **Migration:** Existing `.env` risk parameters must be mapped to the new 8-layer configuration schema.
- **Sign-off:** Requires approval from the Lead Developer (Jules01) and Risk Officer.

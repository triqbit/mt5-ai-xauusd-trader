# Acceptance Criteria: Adaptive Position Sizing Based on Regime Stability

## Functional Acceptance Criteria
- **Behavior:**
    - Dynamically adjust lot sizes based on the statistical "confidence" and "persistence" (stability) of the detected market regime.
    - Scale requested risk by a `SizingMultiplier` derived from the `RegimeStabilityScore` (inverse of GMM entropy or regime duration).
    - "Lean in" (increase exposure) during high-conviction, stable regimes and "step back" (reduce exposure) in fragile or transitional regimes.
- **Edge Cases:**
    - Cap the lot size at the pre-defined mode limits (e.g., Balanced mode cap) regardless of stability to prevent over-leverage.
    - Handle scenarios where regime transition entropy is high (low stability) by applying a minimum floor to the sizing multiplier (e.g., 0.5x).
    - Ensure that sizing adjustments do not violate the global `max_total_heat` limits defined in the `RiskManager`.
- **Inputs/Outputs:**
    - **Inputs:** `RegimeInfo` (with confidence and transition scores), `TradeSignal`, current portfolio heat.
    - **Outputs:** Final lot size for the `TradeSignal` after applying the stability-based multiplier.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the `StabilityMetricEngine` calculating `RegimeStabilityScore` correctly.
    - Unit tests for the `Stability-Risk Mapper` in `CapitalAllocator`.
    - Integration tests verifying that lot sizes are correctly scaled +/- 25% based on simulated regime stability transitions.
- **Performance:**
    - Stability score calculation and sizing adjustment must complete within < 50ms.
- **Error Handling:**
    - If the `RegimeDetector` fails to provide a stability score, default to a neutral (1.0x) multiplier.
- **Observability:**
    - Log the "Sizing Multiplier" and "Stability Score" in every `TradeBriefing` and Audit Log entry.

## Operational Acceptance
- **Documentation:**
    - Update `UNIQUE_FEATURES.md` and `CAPITAL_ALLOCATOR.md` with technical specifications of the stability multiplier logic.
- **Configuration:**
    - Configurable stability tiers and corresponding multipliers (e.g., `STABILITY_MULTIPLIERS: {HIGH: 1.25, MED: 1.0, LOW: 0.5}`).
- **Rollback:**
    - Ability to disable adaptive sizing via a feature flag (`ADAPTIVE_SIZING_ENABLED=FALSE`), reverting to standard ATR-based sizing.
- **Monitoring:**
    - Display current "Regime Stability" and active "Sizing Multiplier" in the Decision Cockpit.

## Release Readiness
- **Deployment:** Integrated into `src/models/regime_detector.py` and `src/trading/capital_allocator.py`.
- **Backward Compatibility:** Must not break existing fixed-sizing or simple ATR-based sizing logic for other symbols.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Quant Research Lead (Jules04) and Core Development Lead (Jules01).

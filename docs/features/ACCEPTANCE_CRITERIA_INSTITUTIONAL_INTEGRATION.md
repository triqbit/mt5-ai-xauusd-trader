# Acceptance Criteria: Institutional Intelligence Integration (Harmonization)

## Functional Acceptance Criteria
- **Behavior:**
    - Harmonize `RegimeDetector`, `CapitalAllocator`, and `DynamicEnsemble` into the main execution loop in `main.py`.
    - `RegimeDetector` output must influence `DynamicEnsemble` weights (e.g., de-weighting LSTM in volatile news regimes).
    - `CapitalAllocator` must dynamically adjust lot sizes based on regime-adjusted confidence.
    - All components must use the same `SignalDirection` and `ModelAction` enums.
- **Edge Cases:**
    - Handle initialization order: Regime detection must occur before model prediction and capital allocation.
    - Graceful degradation: If one component fails (e.g., Regime Detector error), the system must fallback to "Base Mode" (static weights, fixed risk).
- **Inputs/Outputs:**
    - **Inputs:** Raw OHLCV data from MT5.
    - **Outputs:** Executed trade with regime-aware sizing and consensus weighting.

## Technical Acceptance
- **Test Coverage:**
    - Full "Institutional Integration" test suite (`tests/test_institutional_integration.py`).
    - Verification that `EnsembleModel` correctly delegates weighting to `DynamicEnsemble`.
- **Performance:**
    - The end-to-end processing of a tick (Regime -> Prediction -> Allocation -> Execution) must take < 1000ms.
- **Error Handling:**
    - Centralized error handling in `main.py` to prevent component failures from crashing the bot.
- **Observability:**
    - Log the full "Decision Chain" for every tick: `[Regime: Trending] -> [Weights: LSTM 0.7, PPO 0.3] -> [Action: BUY] -> [Sizing: 0.1 Lots]`.

## Operational Acceptance
- **Documentation:**
    - Update `ARCHITECTURE.md` to reflect the harmonized decision flow.
    - Provide a "Harmonization Checklist" for operators.
- **Configuration:**
    - `INTEGRATION_MODE` (string): choice between `legacy` (static) and `institutional` (dynamic).
- **Rollback:**
    - Rapid fallback to `legacy` mode via environment variable.
- **Monitoring:**
    - Track "Component Drift" (how often the regime-aware sizing differs from static sizing).

## Release Readiness
- **Deployment:** This is a major architectural milestone (v1.1.0).
- **Backward Compatibility:** Must support the existing `--algo ensemble` flag while enabling dynamic features under the hood.
- **Migration:** No data migration; logic refactor only.
- **Sign-off:** Requires unanimous approval from Jules01, Jules02, and Jules04.

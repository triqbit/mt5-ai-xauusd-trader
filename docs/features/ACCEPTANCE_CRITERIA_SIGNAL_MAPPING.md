# Acceptance Criteria: Unified Signal Mapping

## Functional Acceptance Criteria
- **Behavior:**
    - Standardize all model outputs and trade signals on the centralized `SignalDirection` (BUY=1, SELL=-1, HOLD=0) and `ModelAction` (HOLD=0, BUY=1, SELL=2) enums in `src/core/constants.py`.
    - All models (`PPOAgent`, `EnsembleModel`, `TimeSeriesTransformer`) must return these standardized types.
- **Edge Cases:**
    - Correct conversion in adapters for external libraries (e.g., Stable-Baselines3 actions to internal `SignalDirection`).
    - Validation that a `HOLD` signal results in zero execution even if confidence is high.
- **Inputs/Outputs:**
    - **Inputs:** Model predictions (integers/floats).
    - **Outputs:** Standardized `Signal` objects with enum-based directions.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for every model's `predict` method to verify return type and mapping.
    - Integration test checking that `OrderManager` receives the correct direction for each enum value.
- **Performance:**
    - Zero performance impact (type mapping only).
- **Error Handling:**
    - Raise a `ValueError` if a model attempts to return a direction outside the defined enum range.
- **Observability:**
    - Log signals using their enum names (e.g., "BUY") instead of raw integers.

## Operational Acceptance
- **Documentation:**
    - Feature in `TECHNICAL_DEBT.md` marked as resolved.
    - Code comments in `src/core/constants.py` explaining the mapping.
- **Configuration:**
    - N/A.
- **Rollback:**
    - N/A (Fundamental structural change).
- **Monitoring:**
    - N/A.

## Release Readiness
- **Deployment:** Mandatory for all future feature branches.
- **Backward Compatibility:** High risk; requires immediate refactoring of any component using raw integers for signals.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Integration Governor (Jules05).

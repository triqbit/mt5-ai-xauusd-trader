# Acceptance Criteria: Resilient Signal Validation

## Functional Acceptance Criteria
- **Behavior:**
    - `RiskEngine.validate_signal` must support both NamedTuples and Pydantic Dataclasses via resilient `getattr` access.
    - Validation must enforce strict range checks for `direction` ({-1, 0, 1}), `confidence` ([0.0, 1.0]), and `volume`.
    - Block any signal with missing mandatory attributes (SL/TP, Ticket ID if closing).
- **Edge Cases:**
    - Handle signals from legacy model versions that might have different attribute names.
    - Graceful rejection of signals with `NaN` or `Inf` values.
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal` (any supported representation).
    - **Outputs:** Boolean `is_valid` and a list of `validation_errors`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests covering all supported signal representations (NamedTuple, Pydantic, dict).
    - Tests for invalid/boundary values for each mandatory field.
- **Performance:**
    - Validation latency < 1ms.
- **Error Handling:**
    - Rejection reasons must be logged with enough detail for model retraining/debugging.
- **Observability:**
    - Log "Signal Validation FAILED" with the specific attribute and value that caused the failure.

## Operational Acceptance
- **Documentation:**
    - Updated `src/core/schemas.py` and `src/trading/risk_engine.py` docstrings.
- **Configuration:**
    - N/A.
- **Rollback:**
    - N/A (Safety improvement).
- **Monitoring:**
    - Track "Signal Validation Failure Rate" per model ID.

## Release Readiness
- **Deployment:** Core component of the v1.1.0-rc4 candidate.
- **Backward Compatibility:** Mandatory support for legacy signal formats to prevent breaking active ensemble members.
- **Migration:** No data migration.
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Security & Quality Lead (Jules02).

# Acceptance Criteria: Capital Allocation System

## Functional Acceptance Criteria
- **Behavior:** Dynamically distribute the total trading budget across multiple strategies while enforcing concentration limits and risk caps.
- **Edge Cases:**
    - Reject allocation if `total_heat` exceeds `max_total_heat`.
    - Enforce `max_symbol_risk` and `max_family_risk` thresholds.
    - Scale requested risk by `performance_multiplier` (0.0 to 2.0).
    - Handle strategy registration and removal without affecting existing allocations.
- **Inputs/Outputs:**
    - **Inputs:** `StrategyConfig`, requested risk percentage.
    - **Outputs:** `AllocationResult` (is_allowed, allocated_amount, risk_pct, rejection_reason).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for budget calculation and limit enforcement.
    - Tests for performance-based scaling logic.
    - Stress tests: concurrent allocation requests (ensure thread safety or atomicity).
- **Performance:**
    - Allocation request processing < 1ms.
- **Error Handling:**
    - Validation of `StrategyConfig` parameters (e.g., `capital_cap` > 0).
    - Clear rejection reasons for each failure mode.
- **Observability:**
    - Log all allocation changes and rejections.
    - Expose current portfolio heat and strategy-level utilization via monitoring.

## Operational Acceptance
- **Documentation:**
    - Reference: [Capital Allocation System](CAPITAL_ALLOCATION.md) (Technical Specs & Usage).
    - Runbook for adjusting global risk caps in production.
- **Configuration:**
    - Global limits (`max_total_heat`, etc.) configurable via `config.yaml`.
- **Rollback:**
    - Support for resetting all allocations to zero in emergency.
- **Monitoring:**
    - Alert if `total_heat` reaches 90% of `max_total_heat`.

## Release Readiness
- **Deployment:** Integrated into the trading loop via `main.py` and `RiskManager`.
- **Backward Compatibility:** Must support single-strategy deployments with default limits.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Risk Committee.

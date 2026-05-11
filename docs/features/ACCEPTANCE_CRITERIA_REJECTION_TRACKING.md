# Acceptance Criteria: Structured Rejection Tracking

## Functional Acceptance Criteria
- **Behavior:**
    - The system must capture and log every instance where a trade signal is rejected by the Risk Manager, Execution Filter, or Capital Allocator.
    - Each rejection must include a standardized reason code (e.g., `INSUFFICIENT_MARGIN`, `MAX_DRAWDOWN_REACHED`, `CONSECUTIVE_LOSS_HALT`).
    - The rejection payload must include the original `TradeSignal` and the specific state variables that triggered the rejection (e.g., current account balance, active position count).
- **Edge Cases:**
    - Handle simultaneous rejections from multiple filters by logging all applicable reason codes.
    - Ensure rejections are logged even if the database is temporarily unreachable (via local file-based fallback).
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal`, `RiskDecision`, `ExecutionDecision`.
    - **Outputs:** Structured log entry in `rejections.json` or equivalent database table; updated "Rejection Rate" metric.

## Technical Acceptance
- **Test Coverage:**
    - 90%+ unit test coverage for the `RejectionTracker` class.
    - Integration test ensuring a rejected signal results in a correctly formatted log entry with a valid `trace_id`.
- **Performance:**
    - Rejection logging latency must be < 5ms to avoid impacting the main loop's responsiveness to subsequent ticks.
- **Error Handling:**
    - The tracker must use non-blocking I/O or a background thread to prevent logging failures from stalling the trading engine.
- **Observability:**
    - Every rejection must be linked to a `trace_id` for end-to-end correlation.
    - Expose `rejection_count` and `rejection_reason_distribution` as Prometheus metrics.

## Operational Acceptance
- **Documentation:**
    - Maintain a "Rejection Reason Dictionary" in the technical docs explaining every code.
- **Configuration:**
    - `REJECTION_LOGGING_LEVEL`: Ability to toggle detailed vs. summary logging.
- **Rollback:**
    - Decoupled from execution logic; safe to disable via feature flag if performance issues occur.
- **Monitoring:**
    - Alert on high rejection rates (>10% of total signals over a 1-hour window) to detect potential misconfiguration or market regime shifts.

## Implementation Details (Jules02)
- **Metric**: `trading_internal_rejections_total` (Prometheus Counter).
- **Labels**: `component` (risk_manager, execution_filter, capital_allocator), `reason` (standardized uppercase strings).
- **Instrumentation**:
    - `RiskManager`/`AuditedRiskManager`: `CIRCUIT_BREAKER`, `DAILY_LOSS`, `MAX_POSITIONS`, `SYMBOL_ALLOCATION`, `MIN_CONFIDENCE`, `RISK_REWARD`, `CONSECUTIVE_LOSSES`, `MODEL_HEALTH`.
    - `ExecutionFilter`: `ATR_VOLATILITY`, `TREND_ANGLE`, `EMA_SEQUENCE`, `MOMENTUM`, `SESSION_CLOSED`, `DRAWDOWN_LIMIT`, `MODEL_STABILITY`, `PERFORMANCE_FLOOR`, `CONFIDENCE_THRESHOLD`, `SIGNAL_FLICKER`, `MACRO_EVENT`.
    - `CapitalAllocator`: `STRATEGY_NOT_FOUND`, `TOTAL_HEAT_LIMIT`, `SYMBOL_CONCENTRATION_LIMIT`, `FAMILY_CONCENTRATION_LIMIT`, `CAPITAL_CAP_REACHED`, `SCALED_TO_ZERO`, `NO_BUDGET`.

## Release Readiness
- **Deployment:** Can be deployed independently as an observability enhancement.
- **Backward Compatibility:** Must be compatible with historical `TradeLogger` records for retrospective analysis.
- **Migration:** No data migration required; new table creation if using a database backend.
- **Sign-off:** Requires approval from the Security & Quality Lead (Jules02).

# Acceptance Criteria: 6-Layer Execution Filter

## Functional Acceptance Criteria
- **Behavior:**
    - Signals must pass all 6 layers (ATR, Trend Angle, EMA Sequence, Momentum, Session, Drawdown) to be approved for execution.
    - If any layer fails, the signal must be blocked, and the specific blocking layer must be identified.
    - The filter must be invoked in the live trading loop before any order is dispatched to MT5.
- **Edge Cases:**
    - Handle missing technical indicators (e.g., EMA200 not yet calculated) by providing a safe fallback or passing the layer with a warning.
    - Validate session times across different time zones, ensuring Sun 17:00 - Fri 16:00 GMT is strictly enforced.
    - Handle high-volatility spikes where ATR exceeds 3x the average ATR.
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal` object, `pd.DataFrame` of market data, current account drawdown percentage.
    - **Outputs:** `ExecutionDecision` object containing approval status, confidence score, and blocking reason (if any).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each individual filter logic (e.g., `_check_ema_sequence`, `_check_momentum`).
    - Integration tests verifying the `validate` method with both passing and failing signal scenarios.
    - Minimum 85% coverage for `src/trading/execution_filter.py`.
- **Performance:**
    - Execution of the full validation cascade must take < 50ms on a standard production CPU.
- **Error Handling:**
    - The filter must not raise exceptions; all internal errors should be caught and return a "Blocked" decision with an error detail.
- **Observability:**
    - Log every decision at `INFO` level, including the blocking reason for rejected signals.
    - Expose the `is_approved` status and `blocked_by` reason to the `TradeSignal` metadata for downstream auditing.

## Operational Acceptance
- **Documentation:**
    - Detailed explanation of each filter layer in the `README.md` or a dedicated doc.
    - Configuration guide for adjusting filter thresholds (e.g., ATR multiplier, RSI zones).
- **Configuration:**
    - Thresholds (ATR threshold, Drawdown limit, RSI periods) must be configurable via environment variables or `config.yaml`.
- **Rollback:**
    - Ability to bypass specific filters (e.g., `SKIP_ATR_FILTER=true`) for testing or emergency maintenance.
- **Monitoring:**
    - Track "Filter Rejection Rate" in Prometheus to identify if specific filters are overly aggressive.

## Release Readiness
- **Deployment:** Part of the core trading engine; must be deployed with the main bot.
- **Backward Compatibility:** Must support the existing `TradeSignal` schema.
- **Migration:** No data migration; logic-only enhancement.
- **Sign-off:** Requires approval from the Core Development Lead (Jules01).

## Implementation Status
- [x] ATR Volatility Filter
- [x] Trend Angle Filter (EMA 21)
- [x] EMA Sequence Filter (8/21/50/200)
- [x] Momentum Filter (RSI)
- [x] Session/Time Filter
- [x] Drawdown Circuit Breaker
- [x] Typed ExecutionDecision output
- [x] Unit tests for all layers

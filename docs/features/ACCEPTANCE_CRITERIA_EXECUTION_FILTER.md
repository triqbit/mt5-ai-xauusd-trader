# Acceptance Criteria: 9-Layer Execution Filter

## Functional Acceptance Criteria
- **Behavior:**
    - Signals must pass all 9 layers to be approved for execution:
        1. **ATR Volatility:** Blocks if ATR > 3x average ATR (volatility spike).
        2. **Trend Angle:** Slope of EMA21 must match signal direction.
        3. **EMA Sequence:** EMA stack (8 > 21 > 50 > 200 for BUY) must be aligned.
        4. **Momentum (RSI):** RSI must be in the healthy pull-back zone (50-75 for BUY, 25-50 for SELL).
        5. **Session/Time:** Institutional hours only (Sun 17:00 - Fri 16:00 GMT).
        6. **Drawdown:** Account drawdown must be below the configured limit (default 15%).
        7. **Model Stability Guard:** Blocks if aggregate model drift or accuracy breaches limits.
        8. **Performance Floor:** Blocks if historical win rate drops below floor (default 40% after 20 trades).
        9. **Confidence Threshold:** Enforces configured minimum confidence (default 0.55).
    - If any layer fails, the signal must be blocked, and the specific blocking layer must be identified in `blocked_by`.
- **Edge Cases:**
    - Handle missing technical indicators by calculating them on-the-fly or providing safe fallbacks.
    - Validate session times correctly across UTC transitions.
    - Gracefully handle cases where `TradeLogger` or `TradingConfig` is not provided (partial validation).
- **Inputs/Outputs:**
    - **Inputs:** `TradeSignal`, `pd.DataFrame` (market data), `current_drawdown`, `model_health` (dict), `TradeLogger`.
    - **Outputs:** `ExecutionDecision` (is_approved, confidence_score, blocked_by).

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for every `_check_*` method in `src/trading/execution_filter.py`.
    - Integration tests for the full `validate` cascade with various failure scenarios.
    - Minimum 90% coverage for the execution filter module.
- **Performance:**
    - Total validation time for all 9 layers must be < 20ms.
- **Error Handling:**
    - The filter must not raise exceptions; internal errors return "Blocked" with details.
- **Observability:**
    - Log every rejection with the specific blocking layer at `INFO` level.
    - Report filter bypasses or data missing warnings at `WARNING` level.

## Operational Acceptance
- **Documentation:**
    - Detailed documentation of all 9 layers in the central feature guide.
- **Configuration:**
    - Every layer threshold (ATR multiplier, Drawdown limit, Win rate floor, etc.) must be configurable via `TradingConfig`.
- **Rollback:**
    - Capability to selectively disable layers for research purposes (e.g., in backtester).
- **Monitoring:**
    - Track per-layer rejection counts in Prometheus to identify "Filter Choke Points".

## Release Readiness
- **Deployment:** Deployed as the primary gate in the `main.py` execution loop.
- **Backward Compatibility:** Must support the existing `TradeSignal` and `ExecutionDecision` schemas.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Core Development Lead (Jules01).

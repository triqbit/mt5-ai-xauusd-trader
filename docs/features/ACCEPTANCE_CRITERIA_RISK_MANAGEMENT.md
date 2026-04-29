# Acceptance Criteria: Risk Management

## Functional Acceptance Criteria
- **Behavior:**
    - The `RiskManager` must implement a 6-layer filter cascade: Circuit Breaker, Daily Loss Limit, Max Positions, Symbol Allocation (All-Weather), Minimum Confidence, and Risk-Reward Ratio.
    - `Circuit Breaker` must halt trading if drawdown exceeds 15%.
    - `Daily Loss Limit` must halt trading if daily realized loss exceeds `max_daily_loss` (default 5%).
    - `Kelly Criterion` must be used for position sizing, capped at 25% fractional Kelly and `risk_per_trade` (max 2% in production).
- **Edge Cases:**
    - Handle zero account balance or peak equity to prevent division by zero.
    - Handle empty approved symbol list.
    - Gracefully handle signals with zero risk (entry == stop loss).
- **Inputs/Outputs:**
    - Input: `TradeSignal` object.
    - Output: Boolean `approve()` result and calculated `lot_size`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each filter layer (at least 90% coverage for `risk_manager.py`).
    - Integration tests verifying signal rejection flow with `TradeLogger`.
- **Performance:**
    - Validation of a single signal must complete in < 10ms.
- **Error Handling:**
    - Log detailed rejection reasons for every rejected signal.
- **Logging/Observability:**
    - Risk events (Circuit Breakers, Limit Hits) must be logged to the database via `TradeLogger`.

## Operational Acceptance
- **Documentation:**
    - `RISK_LIMITS.md` must be updated with current thresholds.
- **Configuration:**
    - Thresholds must be configurable via `TradingConfig` (env variables).
- **Rollback:**
    - Circuit breaker status must be persistable or resettable manually.
- **Monitoring/Alerting:**
    - Circuit breaker activation must trigger a critical alert via `Monitor` (Telegram/Prometheus).

## Release Readiness
- **Deployment:**
    - Can be deployed independently as a core library update.
- **Backward Compatibility:**
    - Must maintain compatibility with existing `TradeSignal` dataclass.
- **Migration:**
    - None required.
- **Stakeholder Sign-off:**
    - Required from Risk Officer/Lead Trader.

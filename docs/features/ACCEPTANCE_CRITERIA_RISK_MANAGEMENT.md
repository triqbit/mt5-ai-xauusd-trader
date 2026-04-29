# Acceptance Criteria: Risk Management Engine

## Functional Acceptance Criteria
- **Behavior:**
  - Must implement a 6-layer filter cascade (Circuit Breaker, Daily Loss, Max Positions, Symbol Allocation, Minimum Confidence, Risk-Reward Ratio).
  - Must calculate position sizing using Fractional Kelly Criterion (capped at 25% Kelly and 2% account risk).
  - Must support Ray Dalio All-Weather portfolio allocation weights.
  - Must automatically halt trading if peak-to-valley drawdown exceeds 15%.
- **Edge Cases:**
  - Handle cases where account balance or equity drops to zero.
  - Handle symbols not present in the `ALLOCATION_WEIGHTS` map.
  - Handle extreme market volatility where ATR-based stops might be excessively large.
- **Inputs/Outputs:**
  - Input: `TradeSignal` object containing symbol, direction, entry, SL, TP, confidence.
  - Output: Boolean `approve()` result and calculated `lot_size`.

## Technical Acceptance
- **Test Coverage:**
  - Unit tests for `RiskManager` covering all 6 filter layers individually.
  - Unit tests for Kelly Criterion calculation with various win/loss ratios.
  - Integration tests verifying `RiskManager` interaction with `TradeLogger` for rejection events.
- **Performance:**
  - Approval logic must execute in < 5ms to minimize total execution latency.
- **Error Handling:**
  - Log specific rejection reasons for every failed signal.
  - Gracefully handle missing `Monitor` or `TradeLogger` instances (optional dependencies).
- **Logging/Observability:**
  - Critical alerts for Circuit Breaker activation.
  - Structured logs for every signal approval/rejection.

## Operational Acceptance
- **Documentation:**
  - Documented risk parameters in `RISK_LIMITS.md`.
  - Runbook for recovering from a Circuit Breaker halt.
- **Configuration:**
  - Configurable via `TradingConfig` (Pydantic): `risk_per_trade`, `max_daily_loss`, `max_positions`.
- **Rollback:**
  - Ability to reset daily stats manually if needed via CLI/API.
- **Monitoring:**
  - Prometheus metrics for daily PnL and current drawdown.
  - Telegram alerts for daily loss limit hits.

## Release Readiness
- **Deployment:**
  - Can be deployed as part of the core trading engine.
- **Backward Compatibility:**
  - Must support existing `TradingConfig` schema.
- **Migration:**
  - No database migrations required for the engine itself, but `TradeLogger` must support risk event logging.
- **Stakeholder Sign-off:**
  - Requires sign-off from Head of Risk and Lead Quant Researcher.

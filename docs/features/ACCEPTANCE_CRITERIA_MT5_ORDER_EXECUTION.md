# Acceptance Criteria: MT5 Order Execution

## Functional Acceptance Criteria
- **Behavior:**
  - Must support market execution for Buy and Sell orders via MetaTrader 5 SDK.
  - Must support automated Stop Loss (SL) and Take Profit (TP) placement at order entry.
  - Must support trailing stops and partial profit taking (scaling out).
  - Must verify connectivity and account status before attempting execution.
- **Edge Cases:**
  - Handle MT5 terminal disconnection during order placement.
  - Handle "Requote" or "Off quotes" errors from the broker.
  - Handle insufficient margin for requested lot size.
  - Handle invalid SL/TP levels (too close to market).
- **Inputs/Outputs:**
  - Input: Validated `TradeSignal` from `RiskManager`.
  - Output: MT5 Ticket ID on success, or detailed error code on failure.

## Technical Acceptance
- **Test Coverage:**
  - Mocked integration tests for `OrderManager` verifying request construction.
  - E2E tests in Demo environment for full execution flow.
- **Performance:**
  - Order submission latency (from `OrderManager` to MT5) < 50ms.
- **Error Handling:**
  - Automatic retry logic for transient network errors (max 3 retries).
  - Immediate notification of execution failure via `Monitor`.
- **Logging/Observability:**
  - Detailed logging of every `buy` and `sell` request/response.
  - Tracking of slippage (difference between requested and actual entry).

## Operational Acceptance
- **Documentation:**
  - `DEPLOYMENT_GUIDE.md` includes MT5 terminal setup.
  - API documentation for `OrderManager` and `MT5Connector`.
- **Configuration:**
  - MT5 login credentials and server managed via `.env` and `TradingConfig`.
- **Rollback:**
  - Emergency "Close All" function to exit all positions instantly.
- **Monitoring:**
  - Alerting on high execution latency or high slippage.
  - Real-time tracking of open positions and margin level.

## Release Readiness
- **Deployment:**
  - Dependent on MT5 terminal availability (Windows or Wine).
- **Backward Compatibility:**
  - Compatible with MT5 Python API 5.0.33+.
- **Migration:**
  - Requires `trade_logs` table in PostgreSQL to store execution details.
- **Stakeholder Sign-off:**
  - Requires sign-off from Lead Trading Engineer.

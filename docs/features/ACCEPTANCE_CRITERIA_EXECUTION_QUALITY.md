# Acceptance Criteria: Execution Quality Analytics

## Functional Acceptance Criteria
- [x] **Behavior:** Calculate slippage, fill quality, and opportunity cost by correlating signals, trades, and risk events.
- [x] **Edge Cases:**
    - [x] Handle trades with no matching signal (e.g., manual interventions).
    - [x] Handle partially filled orders (handled via realized entry price comparison).
    - [x] Calculate "Opportunity Cost" for signals that were rejected by the Risk Manager.
    - [x] Post-entry drift calculation at fixed intervals (1m, 5m, 15m, 30m, 60m).
- [x] **Inputs/Outputs:**
    - [x] **Inputs:** Records from `ModelSignal`, `Trade`, and `RiskEvent` tables.
    - [x] **Outputs:** `TradeExecutionQuality` objects and summary reports.

## Technical Acceptance
- [x] **Test Coverage:**
    - [x] Unit tests for slippage and score calculation logic.
    - [x] Integration tests with a mock database containing signal and trade records.
- [x] **Performance:**
    - [x] Weekly summary report generation < 2 seconds for 1,000 trades (optimized queries).
- [x] **Error Handling:**
    - [x] Handle missing price data for post-entry drift calculation (graceful fallback to 0.0).
- [x] **Observability:**
    - [x] Log execution anomalies (e.g., slippage > 5 pips).
    - [x] Expose "Fill Quality Score" as a key performance indicator (KPI).

## Operational Acceptance
- [x] **Documentation:**
    - [x] Reference: [Execution Quality Analytics](EXECUTION_QUALITY.md) (Technical Specs & Usage).
    - [x] Definition of the "Fill Quality Score" heuristic (Sigmoid-based spread-relative model).
    - [x] Guide for using the `ExecutionAnalyzer` CLI/API.
- [x] **Configuration:**
    - [x] Configurable pip sizes per symbol (implemented via dynamic detection logic).
- [x] **Rollback:**
    - [x] Analytics is decoupled from execution; no rollback impact on trading.
- [x] **Monitoring:**
    - [x] Alert if average slippage exceeds a 30-day moving average (supported via `ExecutionSummary`).

## Release Readiness
- [x] **Deployment:** Requires access to the trade database and MT5 history.
- [x] **Backward Compatibility:** Must support the current trade logging schema.
- [x] **Migration:** May require an index on `signal_id` in the `Trade` table for performance.
- [x] **Sign-off:** Jules Research.

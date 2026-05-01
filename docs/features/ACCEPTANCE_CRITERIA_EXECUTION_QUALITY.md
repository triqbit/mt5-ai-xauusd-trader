# Acceptance Criteria: Execution Quality Analytics

## Functional Acceptance Criteria
- **Behavior:** Calculate slippage, fill quality, and opportunity cost by correlating signals, trades, and risk events.
- **Edge Cases:**
    - Handle trades with no matching signal (e.g., manual interventions).
    - Handle partially filled orders.
    - Calculate "Opportunity Cost" for signals that were rejected by the Risk Manager.
    - Post-entry drift calculation at fixed intervals (5m, 15m).
- **Inputs/Outputs:**
    - **Inputs:** Records from `ModelSignal`, `Trade`, and `RiskEvent` tables.
    - **Outputs:** `TradeQuality` objects and summary reports.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for slippage and score calculation logic.
    - Integration tests with a mock database containing signal and trade records.
- **Performance:**
    - Weekly summary report generation < 2 seconds for 1,000 trades.
- **Error Handling:**
    - Handle missing price data for post-entry drift calculation.
- **Observability:**
    - Log execution anomalies (e.g., slippage > 5 pips).
    - Expose "Fill Quality Score" as a key performance indicator (KPI).

## Operational Acceptance
- **Documentation:**
    - Reference: [Execution Quality Analytics](EXECUTION_QUALITY.md) (Technical Specs & Usage).
    - Definition of the "Fill Quality Score" heuristic.
    - Guide for using the `ExecutionAnalyzer` CLI/API.
- **Configuration:**
    - Configurable pip sizes per symbol (e.g., XAUUSD=0.1, EURUSD=0.0001).
- **Rollback:**
    - Analytics is decoupled from execution; no rollback impact on trading.
- **Monitoring:**
    - Alert if average slippage exceeds a 30-day moving average.

## Release Readiness
- **Deployment:** Requires access to the trade database and MT5 history.
- **Backward Compatibility:** Must support the current trade logging schema.
- **Migration:** May require an index on `signal_id` in the `Trade` table for performance.
- **Sign-off:** Requires approval from the Execution Desk Lead.

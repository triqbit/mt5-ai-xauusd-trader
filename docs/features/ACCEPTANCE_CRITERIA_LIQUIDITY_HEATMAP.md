# Acceptance Criteria: Institutional Liquidity & Order Flow Heatmap

## Functional Acceptance Criteria
- **Behavior:**
    - Real-time tracking and visualization of XAUUSD Depth of Market (DOM) levels.
    - Identification of "Liquidity Pools" (high volume concentrations) and "Liquidity Gaps" (low volume areas).
    - Provide an "Order Imbalance" metric (Bid vs. Ask volume ratio) at each price level.
    - Dynamic adjustment of execution confidence based on the thickness of the order book.
- **Edge Cases:**
    - Handle rapid order book updates during high-volatility events (e.g., NFP) without crashing the UI.
    - Detect "Spoofing" patterns where large orders are repeatedly placed and canceled.
    - Gracefully handle situations where the broker stops providing DOM data.
- **Inputs/Outputs:**
    - **Inputs:** MT5 Level 2 (DOM) stream.
    - **Outputs:** `LiquidityProfile` object, real-time heatmap rendering in the Decision Cockpit, and `liquidity_score` for the `ExecutionFilter`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for order imbalance and liquidity clustering algorithms.
    - Integration tests verifying DOM data ingestion from a mock MT5 stream.
    - Performance benchmarks for heat-map rendering in the TUI.
- **Performance:**
    - DOM data processing and signal injection latency must be < 50ms.
    - Visualization updates must not exceed 5% CPU overhead on standard VPS.
- **Error Handling:**
    - If DOM data is unavailable, the system must fallback to standard spread-based filters.
- **Observability:**
    - Log "High Liquidity Concentration" and "Liquidity Gap" events to the trade logger.
    - Display a "DOM Connectivity" health status in the Cockpit.

## Operational Acceptance
- **Documentation:**
    - Update `RESEARCH.md` to explain the mathematical model for order flow analysis.
- **Configuration:**
    - `LIQUIDITY_HEATMAP_ENABLED` (bool).
    - `DOM_LEVELS_TO_TRACK` (int, default=10).
    - `LIQUIDITY_SENSITIVITY` (float, 0-1).
- **Rollback:**
    - Disabling the heatmap must immediately stop DOM data polling and revert `ExecutionFilter` to base logic.
- **Monitoring:**
    - Monitor DOM stream heartbeat and data integrity.

## Release Readiness
- **Deployment:** Bundled with the high-frequency data ingestor and Decision Cockpit updates.
- **Backward Compatibility:** Must not interfere with standard Price/Volume data streams.
- **Migration:** No database migration required (unless historical DOM logging is enabled).
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Quant Lead (Jules04).

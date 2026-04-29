# Acceptance Criteria: MT5 Order Execution

## Functional Acceptance Criteria
- **Behavior:**
    - Support dual-path execution: Native MT5 Windows SDK and MetaAPI Cloud fallback.
    - Successfully place Market orders (BUY/SELL) with SL/TP.
    - Retrieve real-time ticks (bid/ask) and account info (balance, equity).
    - Support order filling types (IOC) and time-in-force (GTC).
- **Edge Cases:**
    - Handle MT5 terminal disconnection and automatic reconnection.
    - Handle MetaAPI token expiration or API downtime.
    - Prevent execution if prices are invalid (0.0).
- **Inputs/Outputs:**
    - Input: `TradeSignal` or execution parameters (symbol, volume, etc.).
    - Output: Order ticket ID (integer) or error code.

## Technical Acceptance
- **Test Coverage:**
    - Integration tests using `pytest-mock` to simulate MT5/MetaAPI responses.
    - Verification of connection state management.
- **Performance:**
    - Order submission latency < 500ms (excluding network/broker latency).
- **Error Handling:**
    - Catch and log all MT5 retcodes (e.g., `TRADE_RETCODE_DONE`, `TRADE_RETCODE_REQUOTE`).
- **Logging/Observability:**
    - Log all order requests and responses with full metadata.

## Operational Acceptance
- **Documentation:**
    - Setup guide for MT5 terminal and MetaAPI credentials in `SETUP_GUIDE.md`.
- **Configuration:**
    - Configurable `mt5_path`, `login`, `server` via environment variables.
- **Rollback:**
    - Capability to cancel pending orders or close positions.
- **Monitoring:**
    - Alert on persistent connection failures (> 3 attempts).

## Release Readiness
- **Deployment:**
    - Dependent on `MetaTrader5` (Windows) or `metaapi-cloud-sdk` (Linux/Mac).
- **Backward Compatibility:**
    - Maintain consistent `MT5Connector` API (`connect`, `place_order`, `shutdown`).
- **Migration:**
    - Validate environment variable naming (MT5_LOGIN, etc.).
- **Stakeholder Sign-off:**
    - Required from Trading Infrastructure Engineer.

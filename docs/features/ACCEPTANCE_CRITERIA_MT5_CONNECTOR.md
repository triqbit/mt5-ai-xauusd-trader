# Acceptance Criteria: Dual-Path MT5 Connector

## Feature Overview
The `MT5Connector` provides a unified interface for interacting with MetaTrader 5, supporting both the native Windows SDK and a cloud-based fallback via MetaAPI for cross-platform compatibility.

## Functional Acceptance Criteria
- **Behavior**: Implements a dual-path initialization strategy (Native SDK -> MetaAPI Fallback).
- **Edge Cases**:
    - **Native Failure**: Fall back to MetaAPI if native `mt5.initialize()` fails.
    - **Connection Loss**: Detection of lost connection and automatic re-initialization attempts.
- **Inputs/Outputs**:
    - **Rates**: Returns pandas DataFrame with OHLCV data.
    - **Order Execution**: Accepts `TradeSignal` and returns a ticket ID or None on failure.

## Technical Acceptance
- **Test Coverage**:
    - **Unit**: 80%+ coverage for `src/trading/mt5_connector.py`.
    - **Integration**: Mocks for SDKs to verify connection logic.
- **Performance**:
    - **Latency**: `get_rates` < 50ms (Native) or < 500ms (MetaAPI).
- **Error Handling**: Handle and log all MT5 retcodes (e.g., `TRADE_RETCODE_REQUOTE`).
- **Logging/Observability**: Log all connection attempts, successes, and failures. No credentials in logs.

## Operational Acceptance
- **Documentation**: Runbook for setting up MT5 on Windows and MetaAPI on Linux/Docker.
- **Configuration**: Credentials (`MT5_LOGIN`, etc.) managed via environment variables.
- **Rollback Considerations**: Switching back to a previous version of the connector if API changes cause issues.
- **Monitoring/Alerting**: Heartbeat alerts if connection to terminal/cloud is lost for > 60 seconds.

## Release Readiness
- **Deployment**: Deployable independently.
- **Backward Compatibility**: Interface must remain consistent for `RiskManager` and `OrderManager`.
- **Migration Requirements**: None.
- **Stakeholder Sign-off**: DevOps/Infrastructure sign-off for MetaAPI integration security.

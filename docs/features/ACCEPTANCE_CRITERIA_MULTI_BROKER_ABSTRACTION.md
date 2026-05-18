# Acceptance Criteria: Multi-Broker Abstraction Layer

## Functional Acceptance Criteria
- **Behavior:**
    - Provide a standardized, broker-agnostic interface (`BrokerInterface`) for all trading operations (connect, order, cancel, account_info).
    - Implement concrete adapters for MT5 (standard), MetaAPI (cloud/redundant), and potentially Interactive Brokers or CCXT.
    - Ensure unified error mapping across different broker APIs (e.g., both "Invalid Volume" and "Volume Error" map to `InvalidOrderError`).
    - Support "Dual-Execution" or "Shadow Mode" where signals are dispatched to two different brokers for comparison or redundancy.
- **Edge Cases:**
    - Handle differing precision/lot-size requirements between brokers.
    - Resolve "Order ID" mapping when a signal is tracked across multiple broker sessions.
- **Inputs/Outputs:**
    - **Inputs:** Standardized `TradeSignal` and `ExecutionDecision`.
    - **Outputs:** Unified `BrokerResponse` with consistent status codes and ticket IDs.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for each broker adapter using comprehensive mocks.
    - Protocol/Interface tests ensuring all adapters implement mandatory methods.
    - Cross-broker validation tests ensuring consistent behavior for identical signals.
- **Performance:**
    - Latency overhead for the abstraction layer must be < 0.5ms.
- **Error Handling:**
    - Centralized "Broker Health Monitor" that can trigger an automatic failover to a redundant adapter.
- **Observability:**
    - Log "Broker Failover" events with high priority.
    - Include `broker_id` and `adapter_version` in every trade log.

## Operational Acceptance
- **Documentation:**
    - Instructions for implementing new broker adapters.
    - Comparison matrix of supported broker features.
- **Configuration:**
    - `ACTIVE_BROKER_ADAPTER`: e.g., "MT5_LOCAL", "METAAPI_CLOUD".
    - `FAILOVER_ADAPTER_ENABLED`: (bool).
- **Rollback:**
    - Ability to switch back to the native MT5 connector via a single config change.
- **Monitoring:**
    - Alert if any active broker adapter reports a connection loss > 5 seconds.

## Release Readiness
- **Deployment:** Major architectural shift for v1.5.0; requires staged rollout.
- **Backward Compatibility:** Original MT5 connector must be preserved as the "Base Adapter".
- **Migration:** No data migration; requires updates to `src/trading/execution.py`.
- **Sign-off:** Requires approval from the Core Lead (Jules01) and Release Reliability Lead (Jules03).

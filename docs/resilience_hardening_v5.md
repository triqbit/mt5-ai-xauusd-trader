# Resilience Hardening v5

This document describes the hardening of the MT5Connector execution path and enhanced circuit breaker observability.

## Key Changes
- Enhanced `CircuitBreaker` to report state transitions (`CLOSED`, `OPEN`, `HALF_OPEN`) to Prometheus via `Monitor`.
- New metric: `trading_circuit_breaker_state` (0=CLOSED, 1=HALF_OPEN, 2=OPEN).
- Wrapped `MT5Connector.place_order` with the circuit breaker to prevent execution during outages.
- Refactored `main.py` startup sequence to initialize `Monitor` before `MT5Connector`, ensuring startup diagnostics are captured.
- Added explicit connection loss detection for MetaAPI during order placement.
- Hardened `place_order` logic with internal retry and circuit breaking coordination.

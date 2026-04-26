# Error Handling and Recovery System

This document outlines the robust error handling and automatic recovery mechanisms implemented in the MT5 AI/ML Trading Bot.

## Core Components

### 1. Circuit Breaker (`src/core/error_handler.py`)
Protects external dependencies (MetaTrader 5, MetaAPI, Telegram) from being overwhelmed during outages.
- **CLOSED**: Normal operation.
- **OPEN**: Failures exceeded threshold (default: 5). Requests are blocked for a recovery timeout (default: 60s).
- **HALF_OPEN**: After timeout, one request is allowed through to test connectivity.

### 2. Exponential Backoff
Handles transient network failures by retrying operations with increasing delays.
- Used in `MT5Connector.initialize()` to ensure stable connections.

### 3. Dead Letter Queue (DLQ)
Failed trades or critical system events are logged to the `dead_letter_events` table for manual audit and intervention.
- Includes `correlation_id` for tracing errors across logs and database.

### 4. Graceful Degradation
- **Models**: If the `EnsembleModel` fails during inference, it returns a `HOLD` signal instead of crashing the system.
- **Data Sources**: The `MT5Connector` automatically falls back to MetaAPI if the native Windows SDK is unavailable.

## Failure Modes and Responses

| Failure Mode | System Response | Operator Action |
|--------------|-----------------|-----------------|
| MT5 Connection Loss | Exponential backoff retries. If persistent, circuit breaker opens. | Check MT5 Terminal status and internet connection. |
| Model Inference Error | Logged via `ErrorHandler`, degrades to `HOLD`. | Inspect model files and GPU/CPU resource usage. |
| Telegram API Outage | Circuit breaker opens to prevent loop blocking. | Check Telegram Bot token and API status. |
| System Crash/Restart | `RiskManager.recover_state()` reloads open positions and daily PnL from DB. | Verify database integrity and check logs for crash cause. |
| Database Connection Error | Critical failure, system aborts. | Ensure PostgreSQL/SQLite is reachable. |

## Structured Logging

The system uses `structlog` for machine-readable logs.
Key fields to look for:
- `event`: e.g., `error_occurred`, `circuit_breaker_opened`.
- `correlation_id`: Unique ID to track a specific request flow.
- `error`: The raw exception message.
- `action`: What the system was doing when the error occurred.

## Interpreting Alerts

- **🚨 CRITICAL**: Circuit Breaker Triggered. The system has stopped trading due to extreme drawdown or persistent connectivity failures.
- **⚠️ WARNING**: Model Confidence Degradation. Models are producing low-certainty signals; the system may stay in `HOLD` mode.
- **ℹ️ INFO**: State Recovery. Logged during startup when the system successfully restores previous state.

## Manual Intervention (DLQ)

If an event appears in the `dead_letter_events` table:
1. Fetch the `payload` and `error_message` using the `correlation_id`.
2. Resolve the underlying issue (e.g., manual trade reconciliation).
3. Mark the event as `resolved=True` in the database.

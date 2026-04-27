# Error Handling and Recovery System

This document describes the robust error handling and automatic recovery mechanisms implemented in the MT5 AI/ML Trading Bot.

## Core Components

### 1. Circuit Breaker (`src/core/error_handler.py`)
Protects the system from cascading failures by halting calls to failing external APIs (e.g., MetaAPI).
- **CLOSED**: Normal operation.
- **OPEN**: Failures exceeded threshold. API calls are blocked for a recovery timeout.
- **HALF_OPEN**: Recovery timeout expired. One trial call is allowed to check if the service is back.

### 2. Exponential Backoff (`retry_with_backoff`)
Used for transient failures, such as network blips during MT5 connection initialization. It retries the operation with increasing delays.

### 3. Dead Letter Queue (DLQ)
Failed trades, critical API errors, or unhandled exceptions are logged to the `dead_letter_logs` table in the database.
- **Payload**: JSON representation of the failed event.
- **Stack Trace**: Full traceback for debugging.
- **Correlation ID**: Unique ID to trace the error across logs.

### 4. Graceful Degradation
- **Models**: If individual AI models (PPO, LSTM) fail during inference, the `EnsembleModel` catch the exception and uses remaining models. If all fail, it returns a neutral `HOLD` signal.
- **Connection**: If the primary native MT5 SDK fails, the system automatically falls back to MetaAPI cloud.

### 5. State Recovery
On startup, the `RiskManager` automatically:
- Reloads open positions from the database.
- Re-calculates today's realized PnL and trade count to enforce daily loss limits correctly after a crash or restart.

## Common Failure Modes and Responses

| Failure Mode | System Response | Operator Action |
|--------------|-----------------|-----------------|
| MT5 Terminal Disconnect | Exponential backoff retries. | Check MT5 terminal status/internet. |
| MetaAPI Downtime | Circuit breaker opens. Fallback to native or wait. | Check MetaAPI service status. |
| Model Inference Error | Graceful degradation to HOLD. | Check model files and CUDA/CPU resources. |
| Database Connection Loss | Logging continues to console. DLQ may be delayed. | Check SQLite/Postgres connectivity. |
| System Crash | Automatic state recovery on next startup. | Inspect logs using Correlation ID. |

## Interpreting Logs

We use structured logging (`structlog`). Every error log includes:
- `event_type`: Category of the error (e.g., `TRADING_LOOP_ERROR`).
- `correlation_id`: Search this ID in the `dead_letter_logs` table for full details.
- `error`: Brief error message.

Example query for DLQ:
```sql
SELECT * FROM dead_letter_logs WHERE status = 'PENDING';
```

## Operator Troubleshooting
1. **Identify**: Look for `ERROR` or `CRITICAL` logs in the console.
2. **Trace**: Copy the `correlation_id` from the log.
3. **Inspect**: Check the `dead_letter_logs` table or full debug logs for the stack trace associated with that ID.
4. **Resolve**: Fix the underlying issue (e.g., credentials, disk space) and restart the bot. State recovery will handle the rest.

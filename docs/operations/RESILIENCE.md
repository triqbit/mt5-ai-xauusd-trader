# Resilience Engineering

This document outlines the resilience and error-handling standards for the MT5 AI Trading Bot.

## Exception Hierarchy

All custom exceptions inherit from `TradingError` in `src/core/exceptions.py`.

- `TradingError`: Base exception.
- `MT5Error`: Base for MT5-specific issues.
- `MT5ConnectionError`: Network or terminal connectivity failures.
- `MT5DataError`: Data retrieval failures (OHLCV, ticks).
- `MT5ExecutionError`: Order placement or modification failures.

## Retry Strategy

Critical external dependencies (MT5 terminal, MetaAPI) are protected by a robust retry mechanism defined in `src/core/retry.py`.

### `@with_retry` Decorator

Used to wrap functions that interact with external services. Features include:
- **Exponential Backoff**: Delay increases after each failure.
- **Jitter**: Random noise added to delays to prevent thundering herd problems.
- **Max Retries**: Configurable limit (default: 3).

### Application

- **Connectivity**: `MT5Connector.initialize` retries on connection loss.
- **Market Data**: `get_rates` and `get_tick` retry on transient data errors.

## Loop Recovery

The main trading loop in `main.py` is hardened against crashes:
- Catching `MT5DataError` skips the current iteration and waits for the next cycle.
- Catching `MT5ConnectionError` triggers an active reconnection attempt.
- Critical execution errors are logged but don't halt the entire system.

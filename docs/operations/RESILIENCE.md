# Resilience Engineering

This document outlines the resilience and error-handling standards for the MT5 AI Trading Bot.

## Exception Hierarchy

All custom exceptions inherit from `TradingError` in `src/core/exceptions.py`.

- `TradingError`: Base exception. Includes an `is_retriable` flag (defaulting to `True`).
- `MT5Error`: Base for MT5-specific issues.
- `MT5ConnectionError`: Network or terminal connectivity failures.
- `MT5DataError`: Data retrieval failures (OHLCV, ticks).
- `MT5ExecutionError`: Order placement or modification failures.
- `ConfigurationError`: Permanent environment setup issues (`is_retriable=False`).

## Smart Retry Strategy

Critical external dependencies (MT5 terminal, MetaAPI) are protected by a robust retry mechanism defined in `src/core/retry.py`.

### `@with_retry` Decorator

Used to wrap functions that interact with external services. Features include:
- **Exponential Backoff**: Delay increases after each failure.
- **Jitter**: Random noise added to delays to prevent thundering herd problems.
- **Max Retries**: Configurable limit (default: 3).
- **Retriability Awareness**: Respects the `is_retriable` flag on exceptions. If `False`, it fails immediately without retrying.

### Application

- **Connectivity**: `MT5Connector.initialize` retries on connection loss.
- **Market Data**: `get_rates` and `get_tick` retry on transient data errors. Permanent errors like `RES_E_INVALID_PARAMS` are marked as non-retriable.
- **Execution**: `place_order` retries on transient broker rejections (e.g., `TRADE_RETCODE_REQUOTE`) but fails immediately on permanent ones (e.g., `TRADE_RETCODE_NO_MONEY`, `TRADE_RETCODE_INVALID_VOLUME`).

## Loop Recovery

The main trading loop in `main.py` is hardened against crashes:
- Catching `MT5DataError` skips the current iteration and waits for the next cycle.
- Catching `MT5ConnectionError` triggers an active reconnection attempt.
- Critical execution errors are logged but don't halt the entire system.

## Self-Healing Connector

The `MT5Connector` implements a "Self-Healing" pattern to handle long-term connection instability:
- **Auto-Initialization**: Methods like `get_rates` and `place_order` automatically attempt to initialize the connection if it's detected as down.
- **Connection Loss Detection**: If an API call fails with a connection-related error code (e.g., terminal closed, network lost), the connector resets its internal state. This ensures that the next retry attempt (via `@with_retry`) will trigger a fresh `initialize()` call, effectively re-establishing the session without operator intervention.

## Signal Consistency (Flicker Guard)

To ensure operational stability and prevent rapid, noise-driven execution, the system employs a **Signal Consistency** safety layer within the `ExecutionFilter`:
- **Flicker Detection**: Tracks a sliding window of recent signal directions per symbol.
- **Oscillation Blocking**: Automatically blocks execution if the number of direction changes (e.g., BUY <-> SELL) exceeds a strict threshold within the window.
- **Rationale**: Frequent signal flipping often indicates model instability, high market noise, or regime transitions where predictions are unreliable. By halting execution during these "flickering" periods, the bot avoids unnecessary slippage, commissions, and whipsaw losses.

# Log Sanitization and Secret Masking

## Overview

To ensure production safety and prevent the accidental exposure of sensitive credentials, the MT5 AI Trading Bot implements a centralized **Secret Masking Processor** within its logging pipeline.

This system automatically redacts sensitive information such as:
- MetaTrader 5 account passwords
- Database credentials (including those embedded in connection URLs)
- Telegram bot tokens
- MetaAPI authentication tokens

## Implementation Details

The sanitization logic resides in `src/core/log_config.py`. It uses a `SecretMaskingProcessor` integrated into the `structlog` configuration.

### How it Works

1.  **Dynamic Discovery**: At startup, the processor inspects the `TradingConfig` singleton.
2.  **Type-Based Identification**: It identifies any fields annotated with `pydantic.SecretStr`.
3.  **URL Parsing**: It specifically parses the `DATABASE_URL` using regex to extract and mask the password component while leaving the host and port visible for debugging.
4.  **Runtime Redaction**: Every log event processed by `structlog` is scanned for these discovered secrets. Any occurrences are replaced with `[MASKED]`.

## Configuration

Sanitization is enabled by default in all modes (demo, live, backtest). It is configured within the `configure_logging` function in `main.py`.

```python
# Integration in main.py
def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            get_masking_processor(),  # The masking gate
            structlog.dev.ConsoleRenderer(),
        ],
        ...
    )
```

## Security Impact

- **Secrets Exposure Prevention**: Reduces the risk of credentials leaking into persistent logs, ELK stacks, or developer consoles.
- **Observability with Safety**: Allows for detailed "INFO" and "DEBUG" logging without fear of capturing raw passwords in exception traces or configuration summaries.

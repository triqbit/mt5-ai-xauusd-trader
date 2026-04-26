# Core Module

The `src/core/` package contains essential infrastructure components for the trading bot.

## Components

- **config.py**: Centralized configuration management using Pydantic Settings. Supports environment variables and `.env` files.
- **monitor.py**: Real-time monitoring, equity tracking, and Telegram alerting.
- **trade_logger.py**: Persistent storage for signals, trades, and risk events using SQLAlchemy.

## Usage

```python
from src.core.config import get_config
from src.core.monitor import Monitor

config = get_config()
monitor = Monitor(config)
monitor.log_equity(10500.0)
```

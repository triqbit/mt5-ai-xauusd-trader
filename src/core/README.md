# Core Module

The `src/core` module handles the foundational infrastructure of the trading bot, including configuration management, system monitoring, and trade logging.

## Modules

- **`config.py`**: Centralized configuration management using Pydantic V2. It loads settings from environment variables and `.env` files.
- **`monitor.py`**: Handles real-time system monitoring and alerts, including Telegram integration and model confidence tracking.
- **`trade_logger.py`**: Implements a robust logging system using SQLAlchemy ORM (SQLite/PostgreSQL) to record every signal, trade, and risk event.

## Configuration Usage

Settings can be accessed via the `get_config()` singleton:

```python
from src.core.config import get_config

cfg = get_config()
print(cfg.symbol)  # Default: XAUUSD
```

## Database Schema

The `TradeLogger` manages several tables:
- `model_signals`: Raw predictions from AI models.
- `trades`: Executed trade records with P&L.
- `risk_events`: Log of rejections and circuit breaker activations.
- `performance_metrics`: Periodic snapshots of Sharpe ratio, drawdown, etc.

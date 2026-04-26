# Configuration

The bot is configured using environment variables or a `.env` file.

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MT5_LOGIN` | MT5 account number | `0` |
| `MT5_PASSWORD` | MT5 account password (Required) | |
| `MT5_SERVER` | Broker server name (Required) | |
| `MT5_PATH` | Path to MT5 terminal (Windows only) | `C:/Program Files/...` |
| `MODE` | Execution mode (`demo`, `live`, `backtest`) | `demo` |
| `SYMBOL` | Primary trading symbol | `XAUUSD` |
| `TIMEFRAME` | Primary chart timeframe | `M5` |
| `ALGORITHM` | AI Algorithm (`ppo`, `ensemble`, etc.) | `ensemble` |
| `RISK_PER_TRADE` | Max % balance risk per trade | `0.01` |
| `MAX_DAILY_LOSS` | Max % balance loss per day | `0.05` |
| `DATABASE_URL` | SQLAlchemy database connection string | `postgresql://...` |
| `TELEGRAM_TOKEN` | Telegram Bot API token | |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID for alerts | |

## Validation Rules

- `RISK_PER_TRADE`: Must be between 0.1% and 5%. Values > 2% are rejected in `live` mode.
- `MAX_DAILY_LOSS`: Must be between 1% and 20%.
- `MAX_POSITIONS`: Must be between 1 and 10.

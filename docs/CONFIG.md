# Configuration Documentation

The MT5 AI/ML XAUUSD Trading Bot uses Pydantic-v2 for robust configuration management. Settings are loaded from environment variables or a `.env` file.

## 1. MT5 Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MT5_LOGIN` | `int` | `0` | MT5 account number. |
| `MT5_PASSWORD` | `str` | **Required** | MT5 account password. |
| `MT5_SERVER` | `str` | **Required** | Broker server name. |
| `MT5_PATH` | `str` | `C:/Program Files/...` | Path to MT5 terminal executable (Windows). |

## 2. MetaAPI (Cloud Fallback)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `METAAPI_TOKEN` | `str` | `""` | MetaAPI cloud token. |
| `METAAPI_ACCOUNT_ID` | `str` | `""` | MetaAPI account ID. |

## 3. Trading Parameters

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SYMBOL` | `str` | `XAUUSD` | Primary trading symbol. |
| `TIMEFRAME` | `str` | `M5` | Primary chart timeframe. |
| `MODE` | `Literal` | `demo` | Execution mode: `demo`, `live`, `backtest`. |
| `MAX_POSITIONS` | `int` | `3` | Maximum concurrent open positions (1-10). |
| `RISK_PER_TRADE` | `float` | `0.01` | Risk per trade as a fraction of equity (0.001-0.05). |
| `MAX_DAILY_LOSS` | `float` | `0.05` | Max daily loss as a fraction of equity (0.01-0.20). |
| `CONFIRM_LIVE_TRADING` | `str` | `NO` | Must be `YES` to enable `live` mode. |

## 4. Model Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALGORITHM` | `Literal` | `ensemble` | AI model algorithm. |
| `MODEL_PATH` | `Path` | `models/...` | Path to the trained model file. |
| `DEVICE` | `Literal` | `auto` | Computation device (`cpu`, `cuda`, `mps`, `auto`). |
| `CONFIDENCE_THRESHOLD` | `float` | `0.6` | Minimum model confidence to execute a trade. |

## 5. Database & Monitoring

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | `str` | `postgresql://...` | SQLAlchemy database connection string. |
| `REDIS_URL` | `str` | `redis://...` | Redis connection string for caching/messaging. |
| `PROMETHEUS_PORT` | `int` | `8000` | Port for Prometheus metrics and health checks. |
| `LOG_LEVEL` | `Literal` | `INFO` | Logging level. |
| `TELEGRAM_TOKEN` | `str` | `""` | Telegram Bot API token. |
| `TELEGRAM_CHAT_ID` | `str` | `""` | Telegram Chat ID for alerts. |

## 6. Safety Thresholds

- **Risk Limit**: `risk_per_trade` is strictly capped at **2%** for production safety. Any value above this in `live` mode will trigger a validation error.
- **Circuit Breaker**: The `RiskManager` implements a global circuit breaker that halts trading if account equity drawdown reaches **15%** from its peak.
- **Startup Gate**: The application validates all configurations and performs health checks before starting the trading loop.

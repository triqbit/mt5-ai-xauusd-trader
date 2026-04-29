# Configuration Documentation

This document describes the available configuration options for the MT5 AI/ML Trading Bot.

## Environment Variables

The bot uses Pydantic Settings to manage configuration via environment variables or a `.env` file.

### MT5 Connection
| Variable | Description | Default |
|----------|-------------|---------|
| `MT5_LOGIN` | MT5 account number | `0` |
| `MT5_PASSWORD` | MT5 account password | (Required) |
| `MT5_SERVER` | Broker server name | (Required) |
| `MT5_PATH` | Path to MT5 terminal executable | `C:/Program Files/MetaTrader 5/terminal64.exe` |

### MetaAPI (Cloud Fallback)
| Variable | Description | Default |
|----------|-------------|---------|
| `METAAPI_TOKEN` | MetaAPI cloud token | `""` |
| `METAAPI_ACCOUNT_ID` | MetaAPI account ID | `""` |

### Trading Parameters
| Variable | Description | Default |
|----------|-------------|---------|
| `SYMBOL` | Primary trading symbol | `XAUUSD` |
| `TIMEFRAME` | Primary chart timeframe | `M5` |
| `MODE` | Execution mode (`demo`, `live`, `backtest`) | `demo` |
| `MAX_POSITIONS` | Maximum open positions (1-10) | `3` |
| `RISK_PER_TRADE` | Risk percentage per trade (0.1% - 2%) | `0.01` |
| `MAX_DAILY_LOSS` | Maximum daily loss percentage (1% - 20%) | `0.05` |

### Model Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `ALGORITHM` | Algorithm type (`ppo`, `dreamer`, `lstm`, `ensemble`) | `ensemble` |
| `MODEL_PATH` | Path to the trained model file | `models/trained/ensemble_latest.pt` |
| `TRAIN_STEPS` | Number of training steps | `1,000,000` |
| `DEVICE` | Computing device (`cpu`, `cuda`, `mps`, `auto`) | `auto` |

### Database & Cache
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy database URL | `postgresql://trader:password@localhost:5432/mt5_trades` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

### Monitoring & Alerts
| Variable | Description | Default |
|----------|-------------|---------|
| `PROMETHEUS_PORT` | Port for Prometheus metrics | `8000` |
| `DASHBOARD_PORT` | Port for the dashboard | `8050` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `TELEGRAM_TOKEN` | Telegram Bot API token | `""` |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID for alerts | `""` |
| `CONFIDENCE_THRESHOLD` | Model confidence threshold (0.0 - 1.0) | `0.6` |

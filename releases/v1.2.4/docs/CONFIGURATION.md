# Configuration Reference

This document describes all environment variables used by the MT5 AI/ML Trading Bot.

## 1. MT5 Connection
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MT5_LOGIN` | MT5 account number | `0` | Yes (Live/Demo) |
| `MT5_PASSWORD` | MT5 account password | - | Yes (Live/Demo) |
| `MT5_SERVER` | Broker server name | - | Yes (Live/Demo) |
| `MT5_PATH` | Path to MT5 terminal | `C:/...` | No |

## 2. MetaAPI (Cloud Fallback)
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `METAAPI_TOKEN` | MetaAPI cloud token | - | No |
| `METAAPI_ACCOUNT_ID` | MetaAPI account ID | - | No |

## 3. Trading Parameters
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SYMBOL` | Primary trading symbol | `XAUUSD` | No |
| `TIMEFRAME` | Primary chart timeframe | `M5` | No |
| `MODE` | Execution mode (`demo`, `live`, `backtest`) | `demo` | No |
| `MAX_POSITIONS` | Max concurrent open trades | `3` | No |
| `RISK_PER_TRADE` | Fractional risk (e.g. 0.01 for 1%) | `0.01` | No |
| `MAX_DAILY_LOSS` | Max daily drawdown before halt | `0.05` | No |

## 4. Model & Inference
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ALGORITHM` | AI Algorithm (`ppo`, `lstm`, `ensemble`) | `ensemble` | No |
| `MODEL_PATH` | Path to trained model file | `models/...` | No |
| `DEVICE` | Computation device (`cpu`, `cuda`, `auto`) | `auto` | No |

## 5. Infrastructure
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | SQLAlchemy database URL | `postgresql://...` | Yes |
| `REDIS_URL` | Redis connection URL | `redis://...` | Yes |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, etc) | `INFO` | No |

## 6. Alerts & Monitoring
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_TOKEN` | Telegram Bot API token | - | No |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | - | No |
| `PROMETHEUS_PORT` | Port for metrics scraping | `8000` | No |

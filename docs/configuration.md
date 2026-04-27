# Configuration Guide

The bot uses **Pydantic V2** to manage configuration. Settings are loaded from environment variables or a `.env` file in the project root.

## Environment Variables

### MetaTrader 5 Connection
| Variable | Description | Default |
| :--- | :--- | :--- |
| `MT5_LOGIN` | MT5 account number (Integer) | `0` |
| `MT5_PASSWORD` | MT5 account password | `required` |
| `MT5_SERVER` | Broker server name (e.g., `ICMarkets-Demo`) | `required` |
| `MT5_PATH` | Path to `terminal64.exe` (Windows) | `C:/Program Files/...` |

### MetaAPI (Cloud Fallback)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `METAAPI_TOKEN` | MetaAPI cloud token | `""` |
| `METAAPI_ACCOUNT_ID` | MetaAPI account ID | `""` |

### Trading Parameters
| Variable | Description | Default |
| :--- | :--- | :--- |
| `SYMBOL` | Primary trading symbol | `XAUUSD` |
| `TIMEFRAME` | Chart timeframe (M1, M5, H1, etc.) | `M5` |
| `MODE` | Execution mode (`demo`, `live`, `backtest`) | `demo` |
| `MAX_POSITIONS` | Max concurrent open trades | `3` |
| `RISK_PER_TRADE` | Risk as decimal (0.01 = 1%) | `0.01` |
| `MAX_DAILY_LOSS` | Max daily loss threshold | `0.05` |

### Model Settings
| Variable | Description | Default |
| :--- | :--- | :--- |
| `ALGORITHM` | AI model (`ppo`, `ensemble`, etc.) | `ensemble` |
| `DEVICE` | Computation device (`cpu`, `cuda`, `auto`) | `auto` |
| `CONFIDENCE_THRESHOLD` | Min confidence to trade | `0.6` |

## Example `.env` File

```env
MT5_LOGIN=12345678
MT5_PASSWORD=SecurePassword123
MT5_SERVER=ICMarkets-Demo
MODE=demo
RISK_PER_TRADE=0.01
LOG_LEVEL=DEBUG
```

## Validation Rules

- `risk_per_trade`: Cannot exceed 0.02 (2%) in any configuration.
- `max_daily_loss`: Must be between 0.01 and 0.20.
- `max_positions`: Hard-capped between 1 and 10.

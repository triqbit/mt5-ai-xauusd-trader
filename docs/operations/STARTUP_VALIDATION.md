# Startup Validation Layer

The MT5 Trading Bot includes a mandatory startup validation layer defined in `src/core/config_validator.py`. This layer ensures that the application only starts when it is in a safe and valid configuration.

## Validation Rules

At startup, the `ConfigValidator` performs the following checks:

### 1. MT5 Credentials
- **MT5_LOGIN**: Must be a positive integer.
- **MT5_SERVER**: Must be provided and cannot be "server_name", "test", or "your_server_here".
- **MT5_PASSWORD**: Must be provided and cannot be "password", "test", or "your_password_here".
- **MT5_PATH**: On Windows systems, the specified terminal path must exist on the filesystem.

### 2. Trading Mode Safety
- **LIVE Mode**: If `MODE` is set to `live`, the environment variable `CONFIRM_LIVE_TRADING` must be explicitly set to `YES`. This acts as a safety switch to prevent accidental production execution.

### 3. Secrets & Placeholders
- **DATABASE_URL**: Cannot use the default placeholder credentials (`postgresql://trader:password@localhost:5432/mt5_trades`).
- **TELEGRAM_TOKEN**: Cannot contain placeholder text like "YOUR_TOKEN" or "CHANGE_ME".
- **TELEGRAM_CHAT_ID**: Cannot contain placeholder text like "YOUR_CHAT_ID" or "CHANGE_ME".
- **METAAPI_TOKEN**: Cannot contain placeholder text like "YOUR_TOKEN" or "CHANGE_ME".
- **METAAPI_ACCOUNT_ID**: Cannot contain placeholder text like "YOUR_ACCOUNT_ID" or "CHANGE_ME".

### 4. Model Settings
- **MODEL_PATH**: For non-backtest modes, the model file must exist and be a valid file.

### 5. Risk Parameters
- **RISK_PER_TRADE**: Strictly prohibited if greater than 2% (0.02). Warning if > 1%.
- **MAX_DAILY_LOSS**: Strictly prohibited if greater than 6% (0.06). Warning if > 5%.
- **MAX_POSITIONS**: Strictly prohibited if greater than 10 always.
- **CONFIDENCE_THRESHOLD**: Strictly prohibited if less than 0.50. Warning if < 0.55.
- **MODEL_DRIFT_THRESHOLD**: Warning if set greater than 0.4 (Recommended: 0.3).
- **MODEL_ACCURACY_FLOOR**: Strictly prohibited if less than 0.45.
- **MODEL_WIN_RATE_FLOOR**: Strictly prohibited if less than 0.40.

### 6. Incompatible Settings & Consistency
- **LOG_LEVEL**: Warning if set to `DEBUG` in `live` mode.
- **MAX_POSITIONS**: Limited to 5 in `live` mode for safety.
- **MetaAPI Consistency**: `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` must both be provided if either integration parameter is present.
- **Telegram Consistency**: `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` must both be provided if either integration parameter is present.
- **Backtest mode**: `TELEGRAM_TOKEN` should be disabled (non-critical warning).

## Behavior on Failure

If any **CRITICAL** validation error is detected:
1. The application will log the failure details at the `CRITICAL` level.
2. The launch process will be blocked.
3. The application will exit with status code `1`.

Non-critical errors are logged as `WARNING` but do not block the application launch.

## Integration

The validator is integrated directly into the `main.py` entry point and is executed immediately after the configuration is loaded from environment variables or the `.env` file.

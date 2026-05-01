# Startup Validation Layer

The MT5 Trading Bot includes a mandatory startup validation layer defined in `src/core/config_validator.py`. This layer ensures that the application only starts when it is in a safe and valid configuration.

## Validation Rules

At startup, the `ConfigValidator` performs the following checks:

### 1. MT5 Credentials
- **MT5_LOGIN**: Must be a positive integer.
- **MT5_SERVER**: Must be provided and cannot be "server_name" or "test".
- **MT5_PASSWORD**: Must be provided and cannot be "password" or "test".

### 2. Trading Mode Safety
- **LIVE Mode**: If `MODE` is set to `live`, the environment variable `CONFIRM_LIVE_TRADING` must be explicitly set to `YES`. This acts as a safety switch to prevent accidental production execution.

### 3. Secrets & Placeholders
- **DATABASE_URL**: Cannot use the default placeholder credentials (`postgresql://trader:password@localhost:5432/mt5_trades`).
- **TELEGRAM_TOKEN**: Cannot contain placeholder text like "YOUR_TOKEN".

### 4. Risk Parameters
- **RISK_PER_TRADE**: Strictly prohibited if greater than 2% (0.02).
- **MAX_DAILY_LOSS**: Strictly prohibited if greater than 15% (0.15).

### 5. Incompatible Settings
- **MAX_POSITIONS**: Limited to 5 in `live` mode for safety.
- **TELEGRAM_TOKEN**: Should be disabled in `backtest` mode (non-critical warning).

## Behavior on Failure

If any **CRITICAL** validation error is detected:
1. The application will log the failure details at the `CRITICAL` level.
2. The launch process will be blocked.
3. The application will exit with status code `1`.

Non-critical errors are logged as `WARNING` but do not block the application launch.

## Integration

The validator is integrated directly into the `main.py` entry point and is executed immediately after the configuration is loaded from environment variables or the `.env` file.

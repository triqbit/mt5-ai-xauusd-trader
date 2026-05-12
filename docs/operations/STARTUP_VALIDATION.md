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
Detects default values or placeholder patterns (`YOUR_TOKEN`, `CHANGE_ME`, `YOUR_ACCOUNT_ID`, `YOUR_CHAT_ID`, `123456789`, `YOUR_SERVER_HERE`, `YOUR_PASSWORD_HERE`) in the following fields:
- **DATABASE_URL**
- **TELEGRAM_TOKEN**
- **TELEGRAM_CHAT_ID**
- **METAAPI_TOKEN**
- **METAAPI_ACCOUNT_ID**
- **MT5_SERVER**
- **MT5_PASSWORD**

### 4. Model Settings
- **MODEL_PATH**: For non-backtest modes, the model file must exist and be a valid file.

### 5. Risk Parameters
- **RISK_PER_TRADE**: Strictly prohibited if greater than 2% (0.02). Warning if > 1%.
- **MAX_DAILY_LOSS**: Strictly prohibited if greater than 6% (0.06). Warning if > 5%.
- **MAX_POSITIONS**: Strictly prohibited if greater than 10 always.
- **MIN_CONFIDENCE**: Strictly prohibited if less than 0.50. Warning if < 0.55.
- **MAX_LEVERAGE**: Strictly prohibited if greater than 20. Warning if > 10.
- **MAX_POSITION_SIZE_PCT**: Strictly prohibited if greater than 20%. Warning if > 10%.
- **MAX_DRAWDOWN**: Strictly prohibited if greater than 40%. Warning if > 30%.
- **MODEL_DRIFT_THRESHOLD**: Warning if set greater than 0.3.
- **MODEL_ACCURACY_FLOOR**: Strictly prohibited if less than 0.50.
- **MODEL_WIN_RATE_FLOOR**: Strictly prohibited if less than 0.45.
- **MODEL_CALIBRATION_THRESHOLD**: Strictly prohibited if greater than 0.25.

### 6. Hierarchies & Operational Limits
- **Daily Loss Hierarchy**: L1 < L2 < L3 < Max Daily Loss < Hard Stop.
- **Spread Hierarchy**: Min < Alert < Reduce < Halt.
- **Margin Hierarchy**: Alert < Halt < Liquidation (utilization percentages).
- **Volatility Hierarchy**: High < Very High < Extreme thresholds.
- **MAX_TRADES_PER_DAY**: Limited to 50 per institutional policy.
- **MIN_LOT_SIZE**: Minimum 0.01 lot to prevent rounding errors.

### 7. Incompatible Settings & Consistency
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

## Configuration Transparency & Source Attribution

To improve operator awareness, the system includes features to track and display the origin of each configuration parameter.

### 1. Source Attribution in `--show-config`
Running the bot with the `--show-config` flag displays a table containing all active parameters along with their **Source**:
- **CLI**: The value was explicitly provided as a command-line argument.
- **ENV**: The value was loaded from an environment variable or the `.env` file.
- **DEFAULT**: The system is using its built-in default value.

### 2. Startup Operational Summary
The main startup panel highlights parameters overridden via the CLI with a `(CLI OVERRIDE)` tag. This ensures that operators are aware of any non-standard settings being used for the current session.

## Automated Setup & Hardening

The `main.py` entrypoint includes a **Guided Setup** flow for first-time initialization:
- **Directory Initialization**: Automatically creates required `data/`, `logs/`, and `models/trained/` directories if they are missing.
- **Environment Template**: Offers to initialize a `.env` file from `.env.example`.
- **Security Hardening**: Immediately applies restrictive `0o600` (read/write for owner only) permissions to the generated `.env` file to protect credentials.

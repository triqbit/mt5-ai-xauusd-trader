# Configuration Reference (v1.1.0-rc7)

This document lists the available configuration fields, their types, and descriptions.

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `mt5_login` | `int` | MT5 account number for login | `0` |
| `mt5_password` | `SecretStr` | MT5 account password for authentication | `Required` |
| `mt5_server` | `str` | MT5 broker server name (e.g., Broker-Demo) | `Required` |
| `mt5_path` | `str` | Full path to the MT5 terminal executable (Windows only) | `C:/Program Files/MetaTrader 5/terminal64.exe` |
| `metaapi_token` | `SecretStr` | Authentication token for MetaAPI cloud services | `None` |
| `metaapi_account_id` | `SecretStr` | Unique account identifier for MetaAPI provisioning | `None` |
| `symbol` | `str` | The financial instrument to trade (e.g., XAUUSD) | `XAUUSD` |
| `timeframe` | `VALID_TIMEFRAMES` | The chart timeframe for analysis (e.g., M5, H1) | `M5` |
| `mode` | `Literal['demo', 'live', 'backtest']` | Execution mode: demo, live, or backtest | `demo` |
| `max_positions` | `int` | Maximum number of concurrent open positions permitted | `5` |
| `risk_per_trade` | `float` | Fraction of account equity to risk per trade (e.g., 0.01 = 1%) | `0.01` |
| `max_position_size_pct` | `float` | Max Position Size: 10% of account equity per trade | `0.1` |
| `min_lot_size` | `float` | Min Position Size: 0.01 lot | `0.01` |
| `max_leverage` | `float` | Max Leverage: 10:1 | `10.0` |
| `max_single_direction_pct` | `float` | Max 30% net long OR short | `0.3` |
| `max_total_notional_pct` | `float` | <100% of account equity | `1.0` |
| `margin_alert_pct` | `float` | Alert at 70% margin utilization | `0.7` |
| `margin_halt_pct` | `float` | Halt trading at 80% margin utilization | `0.8` |
| `margin_liquidation_pct` | `float` | Automatic close at 90% margin | `0.9` |
| `max_drawdown` | `float` | Max Equity Drawdown (30%) | `0.3` |
| `enable_macro_guard` | `bool` | Enable automatic execution blocking during high-impact events | `True` |
| `macro_pre_event_minutes` | `dict[int, int]` | Minutes before an event to begin risk reduction/blocking, indexed by Impact Level | `Required` |
| `macro_post_event_minutes` | `dict[int, int]` | Minutes after an event to maintain risk reduction/blocking, indexed by Impact Level | `Required` |
| `max_daily_loss` | `float` | Emergency Stop Level 4: 5% loss | `0.05` |
| `daily_loss_lvl1` | `float` | Level 1 (Yellow Alert): 2% loss | `0.02` |
| `daily_loss_lvl2` | `float` | Level 2 (Orange Alert): 3% loss | `0.03` |
| `daily_loss_lvl3` | `float` | Level 3 (Red Alert): 4% loss | `0.04` |
| `daily_loss_hard_stop` | `float` | Hard Stop: 6% loss | `0.06` |
| `daily_win_cap` | `float` | Daily Win Cap: 10% | `0.1` |
| `max_trades_per_day` | `int` | Max 20 trades per day | `20` |
| `max_losing_streak` | `int` | Halt trading after 3 consecutive losses | `3` |
| `max_winning_streak` | `int` | Alert after 5 consecutive wins | `5` |
| `max_weekly_loss` | `float` | Max Weekly Loss: 10% of account | `0.1` |
| `max_monthly_loss` | `float` | Max Monthly Loss: 15% of account | `0.15` |
| `allocator_max_total_heat` | `float` | Max 70% of budget committed | `0.7` |
| `allocator_max_symbol_risk` | `float` | Max 40% per symbol | `0.4` |
| `allocator_max_family_risk` | `float` | Max 40% per model family | `0.4` |
| `allocator_performance_step` | `float` | Adjustment step for performance | `0.05` |
| `allocator_decay_rate` | `float` | Rate at which multiplier returns to 1.0 | `0.001` |
| `allocator_soft_limit_buffer` | `float` | Buffer for diversification guard | `0.1` |
| `volatility_high_threshold` | `float` | High Volatility (>1.5x normal) | `1.5` |
| `volatility_very_high_threshold` | `float` | Very High Volatility (>2x normal) | `2.0` |
| `volatility_extreme_threshold` | `float` | Extreme Volatility (>3x normal) | `3.0` |
| `max_slippage_pips` | `float` | Max Acceptable Slippage: 1.0 pip | `1.0` |
| `min_spread_pips` | `float` | Min Bid-Ask Spread: <0.5 pips | `0.5` |
| `spread_alert_pips` | `float` | Alert if spread >1.0 pip | `1.0` |
| `spread_reduce_pips` | `float` | Reduce if spread >1.5 pips | `1.5` |
| `spread_halt_pips` | `float` | Halt if spread >2.0 pips | `2.0` |
| `execution_latency_threshold` | `float` | Max allowed execution latency in seconds before alerting | `1.0` |
| `algorithm` | `Literal['ppo', 'dreamer', 'lstm', 'ensemble']` | The ML algorithm architecture to use for signal generation | `ensemble` |
| `model_path` | `Path` | Path to the serialized weights of the trained model | `models / trained / ensemble_latest.pt` |
| `train_steps` | `int` | Number of environment steps for model training | `1000000` |
| `device` | `Literal['cpu', 'cuda', 'mps', 'auto']` | Hardware accelerator for model inference (cpu, cuda, mps, auto) | `auto` |
| `database_url` | `SecretStr` | SQLAlchemy-compatible connection string for the primary database | `postgresql://trader:password@localhost:5432/mt5_trades` |
| `redis_url` | `SecretStr` | Connection URL for the Redis instance used for caching/queuing | `redis://localhost:6379/0` |
| `prometheus_port` | `int` | Network port for exposing Prometheus metrics | `8000` |
| `dashboard_port` | `int` | Network port for the interactive monitoring dashboard | `8050` |
| `log_level` | `Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']` | Granularity of application logs (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `telegram_token` | `SecretStr` | Access token for the Telegram Bot API for real-time alerts | `None` |
| `telegram_chat_id` | `str` | Telegram Chat ID or Group ID where alerts will be sent | `None` |
| `confirm_live_trading` | `str` | Explicit confirmation for LIVE trading (must be 'YES' to start in live mode) | `None` |
| `min_confidence` | `float` | Minimum model confidence score required to execute a signal | `0.55` |
| `confidence_threshold` | `float` | Confidence level below which a warning alert is triggered | `0.6` |
| `consensus_threshold` | `float` | Need 60%+ agreement across ensemble | `0.6` |
| `model_drift_threshold` | `float` | Maximum allowed model drift score before halting trades | `0.3` |
| `model_accuracy_floor` | `float` | Minimum allowed model accuracy score before halting trades | `0.5` |
| `model_win_rate_floor` | `float` | Minimum allowed historical win rate before halting trades | `0.45` |
| `model_calibration_threshold` | `float` | Maximum allowed model calibration error (ECE) before halting trades | `0.25` |
| `data_freshness_threshold` | `int` | Maximum age of market data in seconds before alerting | `300` |
| `outcome_noise_threshold` | `float` | Threshold for price change to be considered significant for outcome tracking (e.g. 0.0001 = 1 pip for XAUUSD) | `0.0001` |
| `signal_flicker_window` | `int` | Window size for signal flicker detection | `6` |
| `max_signal_changes` | `int` | Maximum allowed signal direction changes in window | `3` |

# CLI User Experience

The MT5 AI/ML Trading Bot uses the `rich` library to provide a modern, scannable terminal interface.

## Features

### 1. Real-time Startup Status
During the initialization phase, the bot uses status spinners to indicate progress for:
- MT5 Terminal Connection
- Enterprise Health Checks

### 2. System Health Dashboard
Upon startup, a structured table is displayed showing the health status of all critical components:
- **Liveness**: Basic app responsiveness.
- **Database**: Connectivity to the SQLAlchemy/SQLite backend.
- **MT5**: Active connection to the MetaTrader 5 terminal.
- **Models**: Verification that PPO/LSTM models are loaded.
- **Config**: Validation of environment variables and trading parameters.
- **Disk**: Verification of sufficient logging space.

## Visual Indicators
- [green]HEALTHY[/]: Component is operating normally.
- [yellow]DEGRADED[/]: Component is operational but has warnings.
- [red]FAILED[/]: Critical failure that prevents startup.

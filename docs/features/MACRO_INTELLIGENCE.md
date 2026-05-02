# Macroeconomic Event Intelligence

## Overview
The Macro Intelligence system makes the trading bot aware of high-impact macroeconomic events (e.g., CPI, NFP, FOMC). It prevents the bot from entering high-risk trades during volatile news releases and adjusts position sizes during periods of elevated macro risk.

## Components

### `MacroEvent` Model
A structured Pydantic model representing an economic event, including its impact level (LOW, MEDIUM, HIGH) and scheduled timestamp.

### `EventIntelligence` Class
Responsible for:
- Managing the cache of upcoming macro events.
- Determining if the current time falls within a risk window.
- Providing trade blocking signals for high-impact events.
- Calculating risk multipliers for medium-impact events.

### `RiskManager` Integration
The `RiskManager` uses `EventIntelligence` as a filter layer:
- **Execution Blocking**: Trades are automatically rejected if a HIGH impact event is active within the configured pre/post windows.
- **Dynamic Sizing**: Position sizes are reduced (default 50%) during MEDIUM impact windows.

## Configuration
Key settings in `TradingConfig`:
- `enable_macro_filter`: Master toggle for the system.
- `macro_event_high_pre`: Minutes before a HIGH impact event to start blocking.
- `macro_event_high_post`: Minutes after a HIGH impact event to stay blocked.
- `macro_event_medium_pre`: Minutes before a MEDIUM impact event to reduce sizing.
- `macro_event_medium_post`: Minutes after a MEDIUM impact event to restore sizing.

## Usage
The system refreshes event data periodically (every 6 hours) in the live trading loop to ensure the bot always has the latest schedule.

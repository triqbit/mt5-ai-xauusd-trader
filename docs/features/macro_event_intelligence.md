# Macroeconomic Event Intelligence

## Overview
The Macroeconomic Event Intelligence system enables the XAUUSD trading bot to be aware of and respond to high-impact economic events. This system reduces risk by automatically reduction position sizes or blocking execution entirely during periods of extreme volatility associated with major macro data releases.

## Core Components

### 1. Event Providers
- **MetaAPIEventProvider**: Fetches real-time economic calendar data from MetaAPI.
- **CSVEventProvider**: Ingests curated event data from local CSV files.
- **JSONEventProvider**: Ingests event data from local JSON files.
- **TradingViewEventProvider**: A deterministic mock provider for testing and validation.

### 2. Event Normalization
The system normalizes events into standardized categories:
- **CPI**: Inflation data.
- **NFP**: Employment data.
- **FOMC**: Federal Reserve meetings and statements.
- **RATES**: Interest rate decisions.
- **GEOPOLITICAL**: Conflicts, elections, and political tensions.
- **USD_MACRO**: Broad US economic indicators (GDP, PMI, Retail Sales, etc.).

### 3. Risk Windows
Events are assigned pre-event and post-event risk windows based on their impact level (LOW, MEDIUM, HIGH, CRITICAL) and category.
- **Pre-event**: Blocks or reduces risk in the lead-up to the event.
- **Post-event (Cooldown)**: Maintains reduced risk while the market digests the news.

## Integration

### Execution Filter
The `ExecutionFilter` includes a `macro_event` layer. If a high-impact event is active or within its risk window, the filter will return a `BLOCKED` status, preventing new trades.

### Position Sizing
In the `run_live` loop, the system calculates a `risk_multiplier` based on active events. This multiplier is applied directly to the lot size:
- **Normal**: 1.0 (no reduction)
- **High-impact major event (approaching)**: 0.25 (75% reduction)
- **Critical/Ongoing**: 0.0 (Execution blocked)

## Configuration
Risk windows can be customized in `TradingConfig`:
- `macro_pre_event_minutes`: Dictionary mapping impact level to minutes.
- `macro_post_event_minutes`: Dictionary mapping impact level to minutes.
- `enable_macro_guard`: Boolean to enable/disable the entire system.

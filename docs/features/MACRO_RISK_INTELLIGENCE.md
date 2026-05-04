# XAUUSD Macro Risk Intelligence

## Overview
The `EventIntelligence` module (located in `src/data/event_intelligence.py`) provides institutional-grade macroeconomic event awareness for the XAUUSD trading system. It ingests, normalizes, and analyzes high-impact events to manage trading risk.

## Key Features
- **Sophisticated Event Modeling:** Uses `MacroEvent` Pydantic models to represent economic releases, rate decisions, and geopolitical windows.
- **Duration-Based Events:** Supports ongoing events (e.g., FOMC press conferences) via `end_timestamp`.
- **Category-Specific Windows:** Implements specialized risk windows for major events (FOMC, NFP, RATES), providing wider pre-event and post-event (cooldown) coverage.
- **Risk Multipliers:** Calculates a `risk_multiplier` to reduce position sizes during elevated risk periods.
- **Execution Blocking:** Automatically identifies when trading should be strictly prohibited due to critical events.

## Data Providers
The system supports multiple event sources through the `BaseEventProvider` interface:
- **`MetaAPIEventProvider`:** Fetches real-time economic calendar data from MetaAPI.
- **`JSONEventProvider`:** Allows for local manual event ingestion or overrides via a JSON file.
- **`MockEventProvider`:** Used for testing and simulation.

## Configuration
Risk windows are configurable via `pre_event_minutes` and `post_event_minutes` dictionaries mapping `EventImpact` levels to durations.

## Integration
The module is integrated into the `DecisionSupportSystem` to provide macro context in the pre-trade briefing dashboard.

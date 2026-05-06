# XAUUSD Macro Risk Intelligence

## Overview
The `EventIntelligence` module (located in `src/data/event_intelligence.py`) provides institutional-grade macroeconomic event awareness for the XAUUSD trading system. It ingests, normalizes, and analyzes high-impact events to manage trading risk.

## Key Features
- **Sophisticated Event Modeling:** Uses `MacroEvent` Pydantic models to represent economic releases, rate decisions, and geopolitical windows.
- **Duration-Based Events:** Supports ongoing events (e.g., FOMC press conferences) via `end_timestamp`.
- **Category-Specific Windows:** Implements specialized risk windows for major events (FOMC, NFP, RATES), providing wider pre-event and post-event (cooldown) coverage.
- **Risk Multipliers:** Calculates a `risk_multiplier` to reduce position sizes during elevated risk periods.
- **Execution Blocking:** Automatically identifies when trading should be strictly prohibited due to critical events.
- **Enterprise-Grade Resilience:** Features an internal caching mechanism and robust fallback logic that maintains "elevated risk awareness" even if external data providers fail.
- **Advanced Categorization:** Utilizes keyword-based intelligence to identify geopolitical risks (e.g., "TENSION") and key USD macro drivers (e.g., "TREASURY") beyond standard economic calendar classifications.
- **Timezone Safety:** Standardizes all event processing on timezone-aware UTC datetimes to prevent synchronization bugs.

## Data Providers
The system supports multiple event sources through the `BaseEventProvider` interface:
- **`MetaAPIEventProvider`:** Fetches real-time economic calendar data from MetaAPI.
- **`JSONEventProvider`:** Allows for local manual event ingestion or overrides via a JSON file.
- **`MockEventProvider`:** Used for testing and simulation.

## Configuration
Risk windows are configurable via `pre_event_minutes` and `post_event_minutes` dictionaries mapping `EventImpact` levels to durations.

## Integration
The module is integrated into the `DecisionSupportSystem` to provide macro context in the pre-trade briefing dashboard.
The internal `RiskStatus` model provides structured output for downstream components:
- `is_blocked`: Boolean flag for execution suppression.
- `risk_multiplier`: Floating point value (0.0 to 1.0) for position size adjustment.
- `active_events`: List of events currently influencing the risk profile.
- `reason`: Human-readable explanation of the current risk state.

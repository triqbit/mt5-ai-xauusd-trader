# XAUUSD Macro Risk Intelligence

## Overview
The `EventIntelligence` module (located in `src/data/event_intelligence.py`) provides institutional-grade macroeconomic event awareness for the XAUUSD trading system. It ingests, normalizes, and analyzes high-impact events to manage trading risk.

## Key Features
- **Sophisticated Event Modeling:** Uses `MacroEvent` Pydantic models to represent economic releases, rate decisions, and geopolitical windows. Ingests richer data including `actual`, `forecast`, and `previous` values for enhanced signal attribution.
- **Dynamic Severity Scoring:** The `MacroEvent` model includes a `severity_score` property (0.0 to 1.0) derived from impact level and functional category, enabling granular risk-adjusted execution and position sizing.
- **Duration-Based Events:** Supports ongoing events (e.g., FOMC press conferences) via `end_timestamp`.
- **Category-Specific Windows:** Implements specialized risk windows for major events (FOMC, NFP, RATES), providing wider pre-event and post-event (cooldown) coverage.
- **Risk Multipliers:** Calculates a `risk_multiplier` to reduce position sizes during elevated risk periods.
- **Execution Blocking:** Automatically identifies when trading should be strictly prohibited due to critical events.
- **Enterprise-Grade Resilience:** Features an internal caching mechanism and robust fallback logic that maintains "elevated risk awareness" even if external data providers fail. The system implements a "merge-and-prune" cache strategy, ensuring that new data from one provider doesn't overwrite still-relevant data from others.
- **Advanced Categorization:** Utilizes keyword-based intelligence to identify geopolitical risks (e.g., "TENSION") and key USD macro drivers (e.g., "TREASURY") beyond standard economic calendar classifications.
- **Timezone Safety:** Standardizes all event processing on timezone-aware UTC datetimes to prevent synchronization bugs.

## Data Providers
The system utilizes a multi-provider architecture for redundancy and enhanced coverage:
- **`MetaAPIEventProvider`:** Primary source fetching real-time economic calendar data from MetaAPI, covering USD and major global economies (EU, GB, JP, CH, CN).
- **`GeopoliticalEventProvider`:** Specialized provider for manually curated geopolitical risk windows, supporting both local JSON files and in-memory configurations.
- **`TradingViewEventProvider`:** Secondary (mocked) provider for cross-verification.
- **`JSONEventProvider`:** Allows for local manual event ingestion or overrides via a JSON file.
- **`MockEventProvider`:** Used for testing and simulation.

The `EventIntelligence` orchestrator automatically de-duplicates events appearing across multiple providers.

## Configuration
Risk windows are configurable via `TradingConfig` (defined in `src/core/config.py`):
- `enable_macro_guard`: Boolean flag to enable/disable the automatic execution blocking (Layer 11).
- `macro_pre_event_minutes`: Dictionary mapping `EventImpact` integers (1-4) to minutes before an event.
- `macro_post_event_minutes`: Dictionary mapping `EventImpact` integers (1-4) to minutes after an event (cooldown).

If these parameters are not provided in the configuration, the system falls back to institutional defaults.

## Integration
The module is integrated into the `DecisionSupportSystem` to provide macro context in the pre-trade briefing dashboard.

### Risk Windows and Multipliers
The system implements tiered risk management based on event impact and the calculated `severity_score`:
- **Critical Impact:** Blocks execution (`is_blocked=True`) and sets `risk_multiplier=0.0`.
- **High Impact (Major):** For FOMC, NFP, Interest Rate decisions, **CPI**, and **GEOPOLITICAL** events, a stricter `risk_multiplier=0.25` is applied (capping the severity-derived multiplier), with a minimum 2-hour pre-event window and 3-hour cooldown.
- **High Impact (Generic):** Applies a `risk_multiplier=0.5`.
- **Medium Impact:** Applies a `risk_multiplier=0.75`.
The internal `RiskStatus` model provides structured output for downstream components:
- `is_blocked`: Boolean flag for execution suppression.
- `risk_multiplier`: Floating point value (0.0 to 1.0) for position size adjustment.
- `active_events`: List of events currently influencing the risk profile.
- `reason`: Human-readable explanation of the current risk state.

# 🌍 Macro Event Intelligence System

## 🏛️ Overview
The **Event Intelligence System** is an institutional-grade component designed to make the trading system aware of high-impact macroeconomic and geopolitical events. It provides automated risk modulation, execution blocking, and position sizing adjustments based on a real-time feed of market-moving events.

## 🚀 Key Features
- **Multi-Provider Architecture**: Ingests data from MetaAPI, synthetic TradingView patterns, and manual JSON overrides.
- **Institutional Risk Windows**: Configurable pre-event risk windows and post-event cooldowns.
- **Category-Aware Defaults**:
  - **GEOPOLITICAL**: 24-hour default risk window.
  - **FOMC / RATES**: 4-hour high-impact window.
- **Standard Macro (CPI, NFP)**: 2-hour window (enhanced for persistence).
- **Fail-Safe Modulation**: Supports a `fail_safe_blocked` mode to automatically halt trading if macro data feeds are unavailable.
- **Enhanced Provider Attribution**: Includes a `source` field for clear traceability of event origins (e.g., 'MetaAPI').
- **Smart Caching**: Interval-based refresh mechanism to minimize external API latency and costs.

## 🛠️ Components

### 1. `EventIntelligence` (Orchestrator)
The central engine that aggregates events from providers and calculates the current `RiskStatus`. It handles de-duplication, caching, and window logic.

### 2. `MacroEvent` (Model)
A Pydantic-powered model that normalizes event data. It enforces UTC timezone-awareness, applies category-based default durations, and tracks the `source` provider.

### 3. `RiskStatus` (Output)
A structured packet containing:
- `is_blocked`: Whether execution should be strictly stopped.
- `risk_multiplier`: A 0.0 to 1.0 multiplier for position sizing.
- `active_events`: List of events currently impacting the market.
- `blocking_events`: List of events specifically triggering a block.

## 📊 Event Categories & Impact
| Category | Default Duration | Common Examples |
| :--- | :--- | :--- |
| **CPI** | 2 Hours | Core CPI m/m, Inflation Rate |
| **NFP** | 2 Hours | Non-Farm Payrolls, Unemployment Rate |
| **FOMC** | 4 Hours | FOMC Statement, Fed Press Conference |
| **RATES** | 4 Hours | Interest Rate Decisions, Dot Plot |
| **GEOPOLITICAL** | 24 Hours | Conflict Escalation, Sanctions, Elections |
| **USD_MACRO** | 1 Hour | GDP, PMI, ISM, Retail Sales |

## 🧪 Verification
The system is verified by 30+ unit tests covering:
- Provider resilience and retries.
- Caching and refresh interval logic.
- Risk window calculations (ongoing, pre, post).
- Fail-safe behavior.
- Event normalization and validation.

To run the event intelligence tests:
```bash
PYTHONPATH=. python3 -m pytest tests/test_event_intelligence*
```

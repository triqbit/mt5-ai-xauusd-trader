# Macroeconomic Event Intelligence System

The macroeconomic event intelligence system provides the XAUUSD trading system with deep awareness of market-moving events. It standardizes data from multiple providers to enforce institutional-grade risk guardrails.

## Supported Events

The system specifically targets events with high impact on XAUUSD and USD:
- **CPI / Inflation**: Consumer Price Index, PCE, PPI, and other inflation indicators.
- **NFP / Employment**: Non-Farm Payrolls, unemployment rates, and labor market reports.
- **FOMC**: Federal Reserve meetings, statements, and minutes.
- **Interest Rates**: Central bank rate decisions and monetary policy statements.
- **USD Macro**: Broad US economic indicators like GDP, PMI, and Retail Sales.
- **Geopolitical**: Conflicts, elections, and major geopolitical tensions.

## Risk Windows and Guardrails

### Lead Windows (Pre-Event)
Before an event occurs, the system monitors a lead window. For major events (CPI, NFP, FOMC, RATES), this window is extended to **120 minutes**. During the immediate lead-up (e.g., 60 minutes for major events), execution is strictly **blocked** to avoid slippage during pre-event volatility.

### Digestion Windows (Post-Event)
After an event, the system enforces a digestion window. For major events, this is **180 minutes**. Execution is typically blocked for the first **60 minutes** of this period.

### Dynamic Risk Multiplier
During the digestion window (cooldown), the `risk_multiplier` linearly recovers from its suppressed value (e.g., 0.25 for major events) back to 1.0. This allows for a disciplined and gradual return to normal position sizing as market volatility subsides.

## Data Providers

- **MetaAPI**: Fetches real-time economic calendar data.
- **CSV/JSON**: Local file providers for manually curated events or historical analysis.
- **TradingView (Mock)**: Generates synthetic events for testing and pipeline verification.

## Implementation Details

The system is implemented in `src/data/event_intelligence.py` and uses standardized models defined in `src/data/event_models.py`. It calculates a `RiskStatus` which is consumed by execution filters to modulate trading activity.

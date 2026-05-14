# Acceptance Criteria: Institutional Sentiment & Positioning Intelligence

## Functional Acceptance Criteria
- **Behavior:**
    - Monitor XAUUSD market "crowdedness" by aggregating Commitment of Traders (COT) data and retail sentiment indices.
    - Identify sentiment extremes and positioning divergences as leading indicators of trend exhaustion or reversal.
    - Apply a "Contrarian Veto" in the `ExecutionFilter` when crowdedness scores reach extreme percentiles.
- **Edge Cases:**
    - Handle the inherent reporting lag in COT data (released Fridays for the previous Tuesday) by using positioning momentum.
    - Manage missing or intermittent retail sentiment feeds from brokers.
    - Distinguish between "Smart Money" (Commercials) and "Speculative" (Managed Money) positioning extremes.
- **Inputs/Outputs:**
    - **Inputs:** Weekly CFTC COT CSV/JSON, Daily Retail Sentiment Ratios (Long/Short %), historical positioning distributions.
    - **Outputs:** `CrowdednessScore` (0-100), `SentimentRegime` (Contrarian-Bullish, Neutral, Contrarian-Bearish), `PositioningVelocity`.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for COT data parsing and normalization.
    - Unit tests for `CrowdednessScore` calculation logic.
    - Integration tests verifying the "Contrarian Veto" hook in `ExecutionFilter`.
- **Performance:**
    - Sentiment score calculation and filter application must complete in < 50ms.
    - Data ingestion (weekly/daily) must be non-blocking.
- **Error Handling:**
    - Fallback to "Neutral" sentiment (1.0x multiplier) if data feeds are unavailable for > 7 days.
- **Observability:**
    - Log "Crowdedness Score" and active "Sentiment Veto" in the `TradeBriefing` and Decision Cockpit.

## Operational Acceptance
- **Documentation:**
    - Detailed guide on configuring COT data sources and retail sentiment APIs.
    - Explanation of the Crowdedness Score calculation and threshold logic.
- **Configuration:**
    - `SENTIMENT_EXTREME_THRESHOLD`: Percentile for contrarian veto (default 90).
    - `COT_DATA_PROVIDER`: Configuration for CFTC data ingestion.
- **Rollback:**
    - Ability to disable sentiment-based filtering via `SENTIMENT_FILTER_ENABLED=FALSE`.
- **Monitoring:**
    - Display current "Market Sentiment" and "Institutional Positioning" in the Decision Cockpit.

## Release Readiness
- **Deployment:** Integrated into `src/data/sentiment_intelligence.py` and `src/trading/execution_filter.py`.
- **Backward Compatibility:** No impact on purely technical or macro-based trading modes.
- **Migration:** No database migration required.
- **Sign-off:** Requires approval from the Quant Research Lead (Jules04) and Core Development Lead (Jules01).

# Acceptance Criteria: Trade Journal Mining

## Functional Acceptance Criteria
- **Behavior:** Extract behavioral patterns and strategic insights (session performance, drawdown clusters, profitable concentrations) from historical trade data.
- **Edge Cases:**
    - Correct session attribution for trades spanning multiple sessions.
    - Identification of drawdown clusters across weekends/holidays.
    - Identification of "overtrading" based on configurable session averages.
- **Inputs/Outputs:**
    - **Inputs:** Historical trade database (SQLite/Postgres).
    - **Outputs:** `JournalReport` Pydantic model with session and cluster analysis.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for session time logic (UTC).
    - Tests for drawdown cluster detection algorithm.
    - Verification of overtrading flag logic.
- **Performance:**
    - Full journal mining run < 5 seconds for 5,000 trades.
- **Error Handling:**
    - Handle empty databases or periods with no trading activity.
- **Observability:**
    - Output report to a dedicated `journal_mining.json` file.

## Operational Acceptance
- **Documentation:**
    - Reference: [Trade Journal Mining](JOURNAL_MINING.md) (Technical Specs & Usage).
    - Description of the four global sessions and their UTC offsets.
    - Guide on interpreting "Overtrading" and "Drawdown Cluster" alerts.
- **Configuration:**
    - Configurable thresholds for overtrading (e.g., 150% of average).
- **Rollback:**
    - Decoupled from execution; no rollback impact on trading.
- **Monitoring:**
    - Include journal insights in the daily executive summary.

## Release Readiness
- **Deployment:** Deployable as an independent analytics task.
- **Backward Compatibility:** Must work with all historical `TradeLogger` records.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Chief Strategy Officer.

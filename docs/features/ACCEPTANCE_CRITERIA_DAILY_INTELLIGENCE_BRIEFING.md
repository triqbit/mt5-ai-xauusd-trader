# Acceptance Criteria: Daily Intelligence Briefing

## Functional Acceptance Criteria
- **Behavior:**
    - Generate a daily executive summary of trading performance, model health, and macro context.
    - Include PnL attribution (by regime and model).
    - Summarize major macro events from the previous 24h and upcoming 24h.
- **Edge Cases:**
    - Handle days with zero trades gracefully.
    - Consolidate data even if some reporting sub-systems (e.g., Sentiment) are offline.
- **Inputs/Outputs:**
    - **Inputs:** `TradeLogger` history, `RegimeDetector` logs, `MacroSensitivity` data.
    - **Outputs:** PDF/Markdown report sent to Telegram and stored in the database.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for the report generation templates (Jinja2).
    - Integration test for the daily scheduler and data aggregation logic.
- **Performance:**
    - Report generation must complete in < 30 seconds.
- **Error Handling:**
    - Retry logic for report delivery (Telegram/Email).
- **Observability:**
    - Log report generation success/failure.

## Operational Acceptance
- **Documentation:**
    - Description of all KPIs included in the report.
- **Configuration:**
    - `DAILY_BRIEFING_TIME`: Scheduled time for report generation.
    - `REPORTING_RECIPIENTS`: List of Telegram IDs or emails.
- **Rollback:**
    - N/A (Informational feature).
- **Monitoring:**
    - Alert if the report is not delivered by the scheduled time.

## Release Readiness
- **Deployment:** Integrated with the existing `src/research/reporting.py`.
- **Backward Compatibility:** No impact on trading logic.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Product Steward (Jules05).

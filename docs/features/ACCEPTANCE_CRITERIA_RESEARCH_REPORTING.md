# Acceptance Criteria: Institutional Research Reporting

## Functional Acceptance Criteria
- **Behavior:** Consolidate data from multiple research modules into professional Markdown and Terminal reports.
- **Edge Cases:**
    - Graceful handling of missing report sections (omit from final output).
    - Handling of extremely long executive summaries or conclusion fields.
    - Template rendering errors (fallback to plain text).
- **Inputs/Outputs:**
    - **Inputs:** `ResearchReport` Pydantic model.
    - **Outputs:** `.md` file (Jinja2) or Rich-formatted terminal output.

## Technical Acceptance
- **Test Coverage:**
    - Unit tests for template rendering logic.
    - Tests for `ResearchReport` validation.
    - Terminal formatting tests for each section.
- **Performance:**
    - Report generation (Markdown export) < 500ms.
- **Error Handling:**
    - Capture and log Jinja2 template errors.
- **Observability:**
    - Log the path of every saved research report.

## Operational Acceptance
- **Documentation:**
    - Reference: [Institutional Research Reporting](RESEARCH_REPORTING.md) (Technical Specs & Usage).
    - Catalog of available Jinja2 templates and how to extend them.
- **Configuration:**
    - Output directory for reports configurable via environment variable.
- **Rollback:**
    - Non-intrusive; no impact on core system.
- **Monitoring:**
    - Automated daily research summary generation for the "Operator Review".

## Release Readiness
- **Deployment:** Requires `jinja2` and `rich`.
- **Backward Compatibility:** Templates should support older `ResearchReport` schemas if possible.
- **Migration:** No data migration required.
- **Sign-off:** Requires approval from the Portfolio Manager.

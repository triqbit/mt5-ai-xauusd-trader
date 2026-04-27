# Palette Learnings

## Research Reporting UX
**Learning:** For institutional-grade research summaries, Markdown provides a superior balance between human readability and programmatic generation without the weight of heavy templating engines like Jinja2.
**Action:** Implemented a `string.Template` based reporting engine in `src/research/reporting.py` that separates structure from logic while maintaining zero external dependency for formatting.

## Pydantic v2 Aggregation
**Learning:** Using Pydantic models for nested reporting sections ensures type safety and easy JSON serialization, which is critical for audit-ready trading systems.
**Action:** Developed a nested `ResearchSummary` model that encapsulates distinct reports (Regime, Stress, Drift, etc.) with automatic validation.

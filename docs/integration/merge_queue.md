# Authoritative Merge Queue

This document tracks the integration sequence for multi-agent outputs.

| Priority | Agent | PR / Feature | Status | Target Date |
|----------|-------|--------------|--------|-------------|
| 1 | Jules05 | Harmonization (main.py, Connector) | Active | 2026-04-29 |
| 2 | Jules01 | Async/Sync Connector Alignment | Queued | 2026-04-30 |
| 3 | Jules02 | Manager Interface Standardization | Queued | 2026-04-30 |
| 4 | Jules01 | MetaAPI `place_order` Implementation | Queued | 2026-04-30 |
| 5 | Jules02 | Risk-Centric Logic Consolidation | Queued | 2026-05-01 |

## Risk Classification
- **High**: Live trading logic, risk engine, security, migrations.
- **Medium**: UI/UX, documentation, research modules.
- **Low**: Tooling, linting, logging.

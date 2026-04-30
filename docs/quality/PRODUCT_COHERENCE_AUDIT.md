# Product Coherence Audit - April 2026

## 1. Naming Consistency
**Status: 🟡 Improving**
- **Uniform API Terminology:** The `MT5Connector` uses multiple aliases for the same operations (e.g., `initialize()`/`connect()`, `shutdown()`/`disconnect()`, `get_rates()`/`get_ohlcv()`). While helpful for transition, it creates multiple ways to do the same thing, weakening API clarity.
- **Configuration Standards:** Configuration variables in `src/core/config.py` follow a consistent Pydantic pattern, but some environment overrides in `main.py` use different naming styles than the Pydantic fields.

## 2. UX Consistency
**Status: 🟡 Minimal**
- **CLI Patterns:** The CLI entrypoint `main.py` lacks the `--verbose` flag mentioned in the `README.md`, leading to operator confusion.
- **Output Structure:** Logging is mixed between standard `logging` and `structlog`. A consistent, structured output format is needed for automated parsing and professional appearance.
- **Success Confirmations:** Information regarding order placement and position closing is present but lacks a standardized structure across modules.

## 3. Documentation Coherence
**Status: 🔴 Fragmented**
- **Root Decluttering:** The repository root is cluttered with over 20 `.md` files, making it difficult for new developers to find the primary entry points.
- **Functionality Mismatch:** `README.md` references CLI flags and scripts (e.g., `scripts/backtest.py`) that are either missing or not yet integrated into the main workflow.
- **Runbook Accuracy:** Documentation references paths that have shifted as the `src/` directory evolved.

## 4. Module Boundaries
**Status: 🟢 Solid**
- **Separation of Concerns:** Clear separation between `core`, `models`, `trading`, and `environment`.
- **Dependency Management:** Minimal circular dependencies, though the coupling between `RiskManager` and `TradeLogger`/`Monitor` could be further abstracted via interfaces.

## 5. Institutional Polish
**Status: 🟡 Developing**
- **Error Handling:** Standard exceptions are used, but the system lacks a dedicated "Health Gate" to prevent startup if critical environment variables or connections are missing.
- **Timezone Awareness:** The codebase still uses deprecated `datetime.utcnow()`, which can lead to subtle bugs in cross-timezone trading environments.
- **Data Integrity:** `TradeLogger` uses hardcoded contract sizes for P&L calculations, which reduces trust when trading multiple symbols.

## Remediation Plan
1. **Harmonize Documentation:** Move all root-level standards and guides to a structured `docs/` hierarchy.
2. **Implement Health Gate:** Add a formal `HealthGate` to `src/core/health.py` and integrate it into the `main.py` startup sequence.
3. **CLI & UX Alignment:** Add the missing `--verbose` flag and standardize logging via `structlog`.
4. **Technical Debt Cleanup:** Migrate to timezone-aware `datetime.now(timezone.utc)` and implement symbol-aware contract size mapping in the logger.

---
**Audit performed by: Jules05**
**Date: April 2026**

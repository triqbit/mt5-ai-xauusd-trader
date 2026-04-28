# Product Coherence Audit - April 2026

## 1. Executive Summary
The system provides a solid foundation for algorithmic trading, but currently exhibits "architectural drift" where redundant APIs and messy initialization logic in `main.py` reduce professional polish and operator trust.

**Overall Coherence Score: 6/10**

---

## 2. Naming Consistency
### Findings:
- **API Terminology**: `MT5Connector` uses redundant aliases (`initialize` vs `connect`, `shutdown` vs `disconnect`, `get_rates` vs `get_ohlcv`). This creates confusion for developers.
- **Module Naming**: Consistent use of `src/<layer>/<module>.py`.
- **CLI Commands**: `--mode` and `--algo` are clear, but `main.py` contains placeholders for modes not yet fully implemented or linked (e.g., `backtest` pointing to a missing script).

### Remediation:
- Harmonize `MT5Connector` to use a single, standard API.
- Update `main.py` to use these standard methods.

---

## 3. UX Consistency
### Findings:
- **Initialization Logic**: In `main.py`, `RiskManager` is initialized twice. The second initialization overwrites the first, losing the `TradeLogger` reference.
- **Execution Loop**: `run_live` is called twice in `main.py` with different arguments, which is logically incorrect and would lead to double-execution or failure if the first call didn't block.
- **Error Handling**: MT5 connection failures are handled, but the dual-path logic (Native vs MetaAPI) could be cleaner.

### Remediation:
- Fix `main.py` lifecycle management.
- Ensure only one instance of core managers exists.

---

## 4. Documentation Coherence
### Findings:
- **Root Clutter**: The repository root is cluttered with 20+ markdown files, making it difficult for new operators to find the "source of truth".
- **Broken References**: `main.py` and `README.md` reference `scripts/backtest.py`, which does not exist in the current tree.
- **Stale Examples**: The `Quick Start` in `README.md` is generally accurate but lacks mentions of the required database setup for `TradeLogger`.

### Remediation:
- Restructure documentation into a dedicated `docs/` hierarchy.
- Remove or fix references to missing scripts.

---

## 5. Institutional Polish
### Findings:
- **Hardcoded Thresholds**: `RiskManager` uses a hardcoded confidence threshold (0.55) instead of the `confidence_threshold` defined in `TradingConfig`.
- **Logging**: Good use of `structlog`, but some debug prints might still remain in lower-level modules.

### Remediation:
- Bind all risk parameters to `TradingConfig`.
- Ensure all components use the unified logging configuration.

---

## 6. Audit Result: QUALITY GATE FAILURE
The system requires immediate remediation of the `main.py` logic and documentation restructuring before it can be considered a "coherent product".

**Status**: 🔴 RED (Remediation Required)

# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

**Status Update (May 24, 2026):** Remediation in progress by Jules05 to resolve technical drift between Risk components and module boundary violations in the core package.

## 2. Findings

### A. Naming & Type Consistency
- **Duplicate Enums:** `SignalDirection` is defined in both `src/core/schemas.py` and `src/core/constants.py`. (RESOLVED)
- **Mapping Layers:** Multiple layers of mapping exist between `ModelAction` (0,1,2) and `SignalDirection` (1,-1,0). (HARMOMIZING)
- **Terminology Drift:** "Risk API Drift" detected. `RiskEngine` uses `validate_signal` with 8 layers, while `RiskManager` uses `approve` with 6 layers. Standardizing on `validate_signal` across all risk components. (IN PROGRESS)

### B. Module Boundaries
- **Core Package Bloat:** `src/core` contains `FeatureEngineer`, which belongs in `src/data/feature_engineering.py`. This weakens the separation between system core and data processing. (REMEDIATING)
- **Main Script Complexity:** `main.py` contains the primary trading loop logic, which should be encapsulated in a dedicated `TradingExecutor` within `src/trading/`. (REMEDIATING)

### C. UX & Institutional Polish
- **CLI Terminology:** `argparse` help messages use inconsistent verb patterns. Standardizing on "Verb-first" patterns for better operator clarity. (IN PROGRESS)
- **Logging:** Institutional standards require `structlog` to use keyword-only arguments to avoid `TypeError` risks in production. Audit of legacy positional arguments is ongoing. (IN PROGRESS)

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05 - May 24, 2026)
1. **Relocate Feature Engineering:** Move `FeatureEngineer` to `src/data/` while maintaining backward compatibility in `src/core/__init__.py`.
2. **Harmonize Risk API:** Merge `RiskEngine`'s 8-layer cascade into `RiskManager` and standardize on `validate_signal()`.
3. **Encapsulate Execution:** Extract the trading loop from `main.py` into `src/trading/executor.py`.
4. **Standardize CLI & Logging:** Apply consistent help text patterns and ensure keyword-based logging across the codebase.

### Long-term Recommendations
- **TUI Dashboard:** Transition the CLI from rich-panels to a full TUI (Decision Cockpit) for better operator experience.
- **Dependency Isolation:** Further isolate `talib` dependencies to ensure the system can boot and run diagnostics even in environments with missing C-libraries.

---
**Audit Status:** ✅ RECOVERING (Remediation active)
**Steward:** Jules05 (yxynoty)

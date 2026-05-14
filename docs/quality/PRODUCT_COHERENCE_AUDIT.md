# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

**Status Update (May 15, 2026):** Systematic remediation initiated by Jules05 to consolidate risk management logic, centralize schemas, and refine module boundaries.

## 2. Findings

### A. Naming & Type Consistency
- **Duplicate Enums:** `SignalDirection` was previously fragmented but is now centralized in `src/core/constants.py`.
- **Schema Decentralization:** `RiskDecision` is currently defined in `src/trading/risk_engine.py` instead of the central `src/core/schemas.py`.
- **Mapping Layers:** Multiple layers of mapping exist between `ModelAction` and `SignalDirection`. Standardizing on `SignalDirection` for domain logic.

### B. Module Boundaries
- **Core Package Bloat:** `src/core` contains `feature_engineering.py`, which is a data-processing concern. Moving it to `src/data/` improves domain separation.
- **Risk Management Fragmentation:** Logic is split between `RiskEngine` (8-layer cascade) and `RiskManager` (Kelly sizing, All-Weather allocation). Consolidation into `AuditedRiskManager` is required for a single source of truth.

### C. UX & Institutional Polish
- **CLI Terminology:** `argparse` help messages and flag naming require professional standardization to meet enterprise expectations.
- **Logging:** Transitioning the primary execution path to `structlog` for structured, parseable output.

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05 - May 15, 2026)
1. **Centralize Risk Schema:** Move `RiskDecision` to `src/core/schemas.py` and enforce Pydantic V2 patterns.
2. **Harmonize Risk Management:** Consolidate `RiskEngine` and `RiskManager` into a single `AuditedRiskManager`. Implement the 8-layer safety cascade and ATR-based sizing as the primary standard.
3. **Refactor Module Boundaries:** Move `feature_engineering.py` to `src/data/`.
4. **Main Entrypoint Cleanup:** Standardize CLI flags and help text; ensure `structlog` consistency.

### Verification Criteria
- [ ] No circular dependencies between `core`, `data`, and `trading`.
- [ ] 100% of risk decisions are logged to the audit trail with full trace details.
- [ ] CLI `--help` output is uniform and professional.
- [ ] `tests/test_product_coherence.py` passes with no regressions.

---
**Audit Status:** 🛠️ REMEDIATING
**Steward:** Jules05 (yxynoty)

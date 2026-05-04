# Product Coherence Audit - May 2026

## 🏛️ Executive Summary
This audit evaluates the MT5 AI/ML Trading Bot against enterprise standards for naming consistency, UX coherence, documentation accuracy, and module boundaries. While the system has achieved high functional maturity, several "rough edges" persist that fragment the user experience and weaken architectural integrity.

**Overall Coherence Score: 7.8/10**

---

## 🔍 Detailed Findings

### 1. Naming & Type Consistency
- **Fragmented Core Types:** Fundamental trading structures like `TradeSignal` and `ExecutionDecision` are currently defined deep within the `trading` module. This forces upstream modules (like `core.decision_support`) to have circular or unnecessarily deep dependencies on execution logic.
- **Alias Proliferation:** `MT5Connector` maintains multiple aliases for initialization (`initialize`/`connect`) and shutdown (`shutdown`/`disconnect`). While intended for compatibility, it creates ambiguity for new developers.
- **Mixed Logging Standards:** The system uses both standard `logging` and `structlog` inconsistently across `src/trading` and `src/core`.

### 2. UX & Operator Workflow
- **Output Inconsistency:** `main.py` and `DecisionSupportSystem` mix raw Python `print()` statements with structured `rich` console output. This results in fragmented terminal rendering where professional tables are interrupted by unformatted text.
- **Error Clarity:** Some transient MT5 errors are logged with insufficient context, making it difficult for an operator to distinguish between a broker-side timeout and a local configuration issue.

### 3. Documentation Coherence
- **The "Layer" Discrepancy:** The `README.md` and several module headers still refer to a "6-layer" execution filter, whereas the implementation has matured to a "9-layer" cascade.
- **Stale API References:** Some docstrings in `src/trading/mt5_connector.py` refer to methods that have been refactored or moved to fallback paths.

### 4. Module Boundaries
- **Dependency Inversion Violation:** Core components like `SignalExplainer` and `DecisionSupportSystem` are importing types from the `trading` sub-package, violating the principle that core logic should not depend on implementation-specific trading details.

### 5. Institutional Polish
- **Temporal Consistency:** Multiple files still utilize `datetime.utcnow()`, which is deprecated and can lead to timezone-naive ambiguity. The enterprise standard is `datetime.now(timezone.utc)`.
- **Exception Handling:** While a centralized `exceptions.py` exists, several components still catch generic `Exception` or fail to wrap SDK-level errors into the system's hierarchy.

---

## 🛠️ Remediation Plan

### Immediate Fixes (PR ✨ Jules05)
1. **Consolidate Types:** Move `TradeSignal` and `ExecutionDecision` to a centralized `src/core/types.py`.
2. **Temporal Alignment:** Bulk replace `utcnow()` with `now(timezone.utc)`.
3. **UX Harmonization:** Replace all raw `print()` calls in `main.py` and `decision_support.py` with `console.print()`.
4. **Documentation Sync:** Update all references to the "9-layer" filter architecture.

### Secondary Lane Escalations
- **Jules02 (Hardening):** Standardize all `src/trading` modules to use `structlog` exclusively.
- **Jules01 (Core):** Deprecate method aliases in `MT5Connector` in favor of a single unified API.

---
**Audit performed by:** Jules05 (Product Steward)
**Status:** 🔴 REVISION REQUIRED (Fixes in progress)

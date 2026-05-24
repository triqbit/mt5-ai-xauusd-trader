# Product Coherence Audit - 2026-05-22

## Executive Summary
This audit evaluates the system's coherence across naming, UX, documentation, module boundaries, and institutional polish. While the core logic is robust, there is significant "Fragmentation Debt" between the legacy components and the newer "Harmonized" standards, particularly in the Risk Management and Feature Engineering domains.

**Audit Status: YELLOW (Remediation Required)**

---

## 1. Naming Consistency
- **Issue: Risk Authority Ambiguity**
    - `src/trading/risk_manager.py` defines `RiskManager`.
    - `src/trading/risk_engine.py` defines `RiskEngine`.
    - **Impact**: Confusing for developers; unclear which is the primary authority.
    - **Remediation**: Harmonize around `RiskManager` as the primary interface, deprecating `RiskEngine` or merging its logic.
- **Issue: Terminology Drift**
    - `RiskManager.approve()` vs `RiskEngine.validate_signal()`.
    - **Impact**: Breaking tests and inconsistent API usage in `main.py`.
    - **Remediation**: Standardize on `validate_signal()` across all risk components.

## 2. UX Consistency
- **Issue: Logging Format Violation**
    - Multiple modules (`src/core/database.py`, `src/models/regime_detector.py`, `src/trading/mt5_connector.py`) use positional `%`-style formatting (e.g., `logger.info("msg %s", arg)`).
    - **Impact**: Incompatible with `structlog` keyword-based formatting, causing potential `TypeError` in production logging.
    - **Remediation**: Convert all positional logging to keyword arguments.

## 3. Documentation Coherence
- **Issue: README vs Implementation**
    - `RISK_LIMITS.md` specifies ATR-based sizing and 8-layer cascades, but `RiskManager` (the likely production version) uses Kelly sizing and a 6-layer cascade.
    - **Impact**: Documentation promises institutional features not yet fully present in the default risk manager.
    - **Remediation**: Update `RiskManager` to implement the 8-layer cascade and ATR-based sizing.

## 4. Module Boundaries
- **Issue: Feature Engineering Misplacement**
    - `FeatureEngineer` is located in `src/core/feature_engineering.py`.
    - **Impact**: Violates domain boundary (data vs core).
    - **Remediation**: Relocate to `src/data/feature_engineering.py`.
- **Issue: Circular/Messy Exports**
    - `src/trading/__init__.py` exports both `RiskEngine` and `TradeSignal` (which is already in `src.core.schemas`).
    - **Remediation**: Clean up exports to maintain a clean public API.

## 5. Institutional Polish
- **Issue: Error Handling**
    - `MT5Connector` uses generic `logger.exception("Unexpected error...")` without raising structured `MT5Error` variants in some paths.
    - **Remediation**: Ensure all MT5 operations raise specific exceptions from `src/core/exceptions.py`.

---

## Remediation Plan (Jules05 Immediate Actions)
1. **Relocate Feature Engineering**: Move `src/core/feature_engineering.py` -> `src/data/feature_engineering.py`.
2. **Harmonize Risk API**: Implement `validate_signal()` and ATR-sizing in `RiskManager` and `AuditedRiskManager`.
3. **Fix Logging**: Standardize `src/core/`, `src/trading/`, and `src/models/` to keyword-based logging.
4. **Cleanup Exports**: Align `src/trading/__init__.py` with the harmonized API.

# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

## 2. Findings

### A. Naming & Type Consistency
- **Duplicate Enums:** `SignalDirection` is defined in both `src/core/schemas.py` and `src/core/constants.py`.
- **Mapping Layers:** Multiple layers of mapping exist between `ModelAction` (0,1,2) and `SignalDirection` (1,-1,0), creating confusion in the prediction pipeline.
- **Terminology Drift:** The system uses "Signal", "Action", and "Decision" interchangeably for model outputs. Standardizing on "Signal" for raw model outputs and "Decision" for risk-filtered outputs is recommended.

### B. Module Boundaries
- **Core Package bloat:** `src/core` contains diverse logic (exceptions, constants, schemas, feature engineering). While centralized, some components like `FeatureEngineer` could eventually move to `src/data` if they grow further.
- **Circular Risk:** High potential for circular dependencies when multiple core components import from each other (e.g., `schemas` importing `constants` while `constants` might need types).

### C. UX & Institutional Polish
- **CLI Terminology:** `argparse` help messages are inconsistent in their use of "algorithm" vs "algo" vs "model".
- **Logging:** Structlog is well-integrated, but some legacy `logging.info` calls in `main.py` lack the structured context available in other modules.

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05)
1. **Consolidate Enums:** Move `SignalDirection` and `DecisionStatus` into `src/core/constants.py`.
2. **Harmonize Schemas:** Update `src/core/schemas.py` to import from `constants.py`.
3. **Refactor BaseModel:** Ensure all models return a `Signal` using the unified `SignalDirection`.
4. **Main entrypoint cleanup:** Standardize terminology in CLI flags and help text.

### Long-term Recommendations
- **Domain Separation:** Evaluate moving `feature_engineering.py` to `src/data/`.
- **TUI Dashboard:** Transition the CLI from rich-panels to a full TUI (Decision Cockpit) for better operator experience.

---
**Audit Status:** ⚠️ DEGRADED (Fragmentation debt detected)
**Steward:** Jules05 (yxynoty)

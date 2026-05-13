# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

**Status Update (May 8, 2026):** Remediation in progress by Jules05 to resolve fragmentation debt in CLI, logging, and model output standardization.

## 2. Findings

### A. Naming & Type Consistency
- **Duplicate Enums:** `SignalDirection` is defined in both `src/core/schemas.py` and `src/core/constants.py`. (RESOLVED)
- **Mapping Layers:** Multiple layers of mapping exist between `ModelAction` (0,1,2) and `SignalDirection` (1,-1,0). (HARMOMIZING)
- **Terminology Drift:** Standardizing on "Signal" for raw model outputs and "Decision" for risk-filtered outputs. (IN PROGRESS)

### B. Module Boundaries
- **Core Package bloat:** `src/core` contains diverse logic. Evaluation for future domain separation (e.g., moving FeatureEngineer to `src/data`) is ongoing.
- **Circular Risk:** Centralizing enums in `constants.py` has reduced circular dependency risks between `schemas` and other modules.

### C. UX & Institutional Polish
- **CLI Terminology:** `argparse` help messages are inconsistent. (STANDARDIZING)
- **Logging:** `main.py` transitions from standard `logging` to `structlog` for system-wide consistency. (IN PROGRESS)

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05 - Applied May 8, 2026)
1. **Consolidate Enums:** Move `SignalDirection` and `DecisionStatus` into `src/core/constants.py`. (Verified)
2. **Harmonize Schemas:** Update `src/core/schemas.py` to import from `constants.py`. (Verified)
3. **Refactor BaseModel & Subclasses:** Ensure all models return a `Signal` NamedTuple using `SignalDirection`. (Applied to PPO, LSTM, Transformer, Ensemble)
4. **Main entrypoint cleanup:** Standardize terminology in CLI flags and help text; implement `structlog`. (Applied)

### Long-term Recommendations
- **Domain Separation:** Evaluate moving `feature_engineering.py` to `src/data/`.
- **TUI Dashboard:** Transition the CLI from rich-panels to a full TUI (Decision Cockpit) for better operator experience.

---
**Audit Status:** ✅ RECOVERING (Remediation active)
**Steward:** Jules05 (yxynoty)

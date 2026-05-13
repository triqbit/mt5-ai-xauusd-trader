# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

**Status Update (May 15, 2026):** Remediation in progress by Jules05 to resolve fragmentation debt in CLI, logging, and risk management logic.

## 2. Findings

### A. Naming & Type Consistency
- **Duplicate Enums:** `SignalDirection` is defined in both `src/core/schemas.py` and `src/core/constants.py`. (RESOLVED)
- **Mapping Layers:** Multiple layers of mapping exist between `ModelAction` (0,1,2) and `SignalDirection` (1,-1,0). (RESOLVED)
- **Terminology Drift:** Standardizing on "Signal" for raw model outputs and "Decision" for risk-filtered outputs. (RESOLVED)

### B. Module Boundaries
- **Core Package bloat:** `src/core` contains diverse logic. Evaluation for future domain separation (e.g., moving FeatureEngineer to `src/data`) is ongoing.
- **Risk Management Fragmentation:** Logic is split between `RiskManager` (older interface) and `RiskEngine` (newer logic). This creates confusion and redundant code paths. (REMEDIATING)
- **Circular Risk:** Centralizing enums in `constants.py` has reduced circular dependency risks between `schemas` and other modules. (RESOLVED)

### C. UX & Institutional Polish
- **CLI Terminology:** `argparse` help messages are inconsistent. (STANDARDIZED)
- **Logging:** `main.py` transitions from standard `logging` to `structlog` for system-wide consistency. (RESOLVED)

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05 - Applied May 15, 2026)
1. **Harmonize Risk Management:**
   - Centralize `RiskDecision` in `src/core/schemas.py`.
   - Update `RiskManager` to return `RiskDecision` and accept proper market context (`market_data`, `open_positions`).
   - Delete redundant `src/trading/risk_engine.py`.
2. **Main entrypoint cleanup:** Standardize terminology in CLI flags and help text; implement `structlog`. (Verified)

### Long-term Recommendations
- **Domain Separation:** Evaluate moving `feature_engineering.py` to `src/data/`.
- **TUI Dashboard:** Transition the CLI from rich-panels to a full TUI (Decision Cockpit) for better operator experience.

---
**Audit Status:** ✅ RECOVERING (Remediation active)
**Steward:** Jules05 (yxynoty)

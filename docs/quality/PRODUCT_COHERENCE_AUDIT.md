# Product Coherence Audit - May 2026

## 1. Executive Summary
This audit evaluates the MT5 AI XAUUSD Trader for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical maturity, several areas of "fragmentation debt" have been identified that could reduce operator trust and increase maintenance overhead.

**Status Update (May 13, 2026):** Remediation in progress by Jules05 to resolve fragmentation debt in risk management logic, terminology standardization, and CLI help strings.

## 2. Findings

### A. Naming & Type Consistency
- **Terminology Drift:** Standardizing on "Signal" for raw model outputs and "Decision" for risk-filtered and execution-filtered outputs.
- **Schema Fragmentation:** Domain models like `RiskDecision` and `DailyStats` are currently located in trading modules rather than core schema packages.

### B. Module Boundaries
- **Risk Management Fragmentation:** Two parallel risk systems exist (`RiskManager` and `RiskEngine`). `RiskManager` is currently used in `main.py`, but `RiskEngine` contains more sophisticated institutional logic defined in `RISK_LIMITS.md`.
- **Action:** Consolidate institutional logic into `RiskManager` and deprecate `RiskEngine`.

### C. UX & Institutional Polish
- **CLI Help Strings:** Descriptions for `--algo`, `--mode`, and `--confirm-live` lack the professional, institutional tone expected for an enterprise trading system.
- **Logging Consistency:** Some legacy `logging` calls remain in the primary trading loop, which should be migrated to structured `structlog` for uniform observability.

## 3. Remediation Plan

### Immediate Fixes (PR ✨ Jules05 - May 13, 2026)
1. **Consolidate Risk Logic:** Merge institutional 8-layer cascade and ATR-based sizing from `RiskEngine` into `RiskManager`.
2. **Centralize Schemas:** Move `RiskDecision` and `DailyStats` to `src/core/schemas.py` and convert to Pydantic models.
3. **Harmonize Trading Loop:** Update `main.py` to use the unified risk interface and handle structured decisions.
4. **Professionalize CLI:** Refine argparse help text and ensure system-wide structured logging in the hot path.

### Long-term Recommendations
- **Domain Separation:** Evaluate moving `feature_engineering.py` to `src/data/`.
- **TUI Dashboard:** Transition the CLI from rich-panels to a full TUI (Decision Cockpit) for better operator experience.

---
**Audit Status:** ⚠️ REMEDIATING
**Steward:** Jules05 (yxynoty)

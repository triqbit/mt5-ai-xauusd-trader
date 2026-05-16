# Product Coherence Audit - May 16, 2026

## 📋 Executive Summary
This audit evaluates the MT5 AI/ML Trading Bot for architectural coherence, naming consistency, and institutional polish. While the system demonstrates high technical capability, several points of fragmentation were identified in the core risk management and data processing layers.

## 🔍 Audit Findings

### 1. Naming Consistency & API Uniformity
- **Risk Management Fragmentation**: The system currently maintains two parallel risk components: `RiskEngine` (src/trading/risk_engine.py) and `RiskManager` (src/trading/risk_manager.py).
    - `RiskEngine` implements a modern 8-layer ATR-based cascade.
    - `RiskManager` implements a legacy 6-layer Kelly-based approach.
    - **Impact**: High. Developers and operators may be confused about which risk logic is active.
- **Method Disparity**: `RiskManager` uses `approve()` while `RiskEngine` uses `validate_signal()`.
- **Inconsistent Exports**: `src/trading/__init__.py` exports `RiskEngine` but not the newer `AuditedRiskManager`.

### 2. Module Boundaries
- **Data vs Core**: `FeatureEngineer` is currently located in `src/core/feature_engineering.py`. By institutional standards, feature engineering belongs in the `data` domain.
    - **Impact**: Medium. Weakens domain separation.
- **Circular Dependencies**: Lazy-loading in `src/core/__init__.py` for `FeatureEngineer` indicates a boundary tension that should be resolved by proper relocation.

### 3. Documentation Coherence
- **README Mismatch**: The README mentions a "9-Layer Execution Filter" and "8-layer safety cascade," but the implementation in `RiskManager` is 6-layer.
- **Stale References**: Some docstrings still reference the Kelly Criterion as the primary sizing method, while the system is transitioning to ATR-based institutional sizing.

### 4. Institutional Polish
- **Error Handling**: `main.py` has robust bootstrap error handling, but the transition between `RiskManager` and `MT5Connector` for position tracking is slightly coupled.
- **Graceful Degradation**: The 8-layer cascade in `RiskEngine` provides better degradation (sizing reduction) than the binary `approve()` in `RiskManager`.

## 🛠️ Remediation Plan

| Issue | Action | Priority |
| :--- | :--- | :--- |
| **Risk Fragmentation** | Consolidate 8-layer logic into `RiskManager` and delete `RiskEngine`. | CRITICAL |
| **Domain Misalignment** | Relocate `FeatureEngineer` to `src/data/feature_engineering.py`. | HIGH |
| **API Standardization** | Standardize on `validate_signal()` returning `RiskDecision`. | HIGH |
| **Docs Sync** | Update README and docstrings to reflect 8-layer ATR cascade. | MEDIUM |

## ✅ Status: FIX REQUIRED
The system is technically functional but requires harmonization to maintain "One Coherent Product" status.

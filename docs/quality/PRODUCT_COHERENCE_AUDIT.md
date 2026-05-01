# Product Coherence Audit - May 2026

## Executive Summary
This audit evaluates the MT5 AI/ML Trading Bot for architectural coherence, naming consistency, and institutional-grade polish. While the core modules (Regime Detection, Capital Allocation, Dynamic Ensemble) are technically sound, their integration into the primary trading loop is incomplete, and several naming inconsistencies reduce developer and operator trust.

## 1. Naming Consistency & Terminology
- **Issue**: Duplicated Enums. `SignalDirection` is defined in `src/core/explainability.py` but used implicitly as integers elsewhere. `MarketRegime` is defined in `src/models/regime_detector.py` but not used as a type hint in the `EnsembleModel`.
- **Issue**: CLI/Config Mismatch. `main.py` uses `--algo`, while `TradingConfig` and documentation use `algorithm`.
- **Recommendation**: Centralize all enums in `src/core/constants.py` and enforce type hinting across all modules.

## 2. UX & Operator Workflow
- **Issue**: Fragmented CLI. The `--mode backtest` command is a stub that points to a non-existent `scripts/backtest.py`.
- **Issue**: Hidden Intelligence. Regime detection and capital allocation are running in "stealth mode" or not at all in `main.py`, depriving the operator of institutional-grade decision transparency.
- **Recommendation**: Fully integrate `RegimeDetector` and `CapitalAllocator` into `main.py` and update the logging to reflect their inputs.

## 3. Module Boundaries & Integration
- **Issue**: Direct Coupling. `main.py` performs manual lot sizing logic that should be handled by `CapitalAllocator`.
- **Issue**: Passive Ensemble. `EnsembleModel` does not yet ingest `MarketRegime` context to adjust weights dynamically during live execution (it only uses rolling Sharpe).
- **Recommendation**: Refactor `run_live` to delegate sizing to `CapitalAllocator` and pass regime context to `EnsembleModel`.

## 4. Institutional Polish
- **Issue**: Hardcoded Constants. `TradeLogger` uses a hardcoded `contract_size = 100` for XAUUSD, which will fail for other symbols like EURUSD (100,000).
- **Issue**: Deprecated APIs. Usage of `datetime.utcnow()` throughout the codebase violates PEP 615 and modern Python standards.
- **Recommendation**: Implement a symbol-to-contract-size mapping and migrate to timezone-aware `datetime.now(timezone.utc)`.

## 5. Documentation Coherence
- **Issue**: The `README.md` claims "6-Layer Execution Filter" and "Ray Dalio All-Weather Allocation," but these are currently underutilized in the primary `main.py` entrypoint.
- **Recommendation**: Update `README.md` once the integration of these features is verified in the live loop.

---
**Status**: 🟠 DEGRADED (Coherence)
**Action Plan**: PR "✨ Jules05: Product coherence improvements" will address these gaps.

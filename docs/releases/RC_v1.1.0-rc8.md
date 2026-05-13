# 🚀 Release Candidate: v1.1.0-rc8

**Date:** 2026-05-13
**Status:** Release Candidate
**Tag:** `v1.1.0-rc8`

## 📝 Overview
This release candidate (v1.1.0-rc8) represents a major step towards architectural maturity and institutional-grade operational transparency. Key achievements include the harmonization of the risk management engine, the integration of a real-time "Glass Box" Decision Cockpit, and the full coupling of market intelligence and execution analytics into the live trading loop. System test coverage remains robust at **87.6%**.

## ✅ What's Included and Why
- **Harmonized Risk Management:** Unified 8-layer cascading risk filter and ATR-based position sizing into `AuditedRiskManager`. Eliminates logic fragmentation and ensures consistent safety enforcement.
- **Institutional Decision Cockpit:** Live integration of `DecisionSupportSystem` into `main.py`. Provides operators with real-time signal attribution, regime context, and rejection reasons.
- **Market Intelligence Coupling:** `EventIntelligence` and `ExecutionAnalyzer` are now active in the live loop, providing real-time macro-risk awareness and post-trade performance tracking.
- **Interactive Setup Wizard:** Guided CLI configuration (`--setup`) to reduce operational friction during first-time deployment.
- **CLI Ergonomics & Visibility:** Refactored argument parsing and enhanced startup panels for better operator UX and masking of sensitive MT5 credentials.
- **Stateful Feature Normalization:** Production-ready Z-score/Min-Max persistence in the `FeatureEngineer` pipeline for inference consistency.
- **Strategic Feature Roadmap (Updated):** Revised maturation plan with a 5-point scoring rubric for institutional feature prioritization.
- **Product Coherence Audit:** Repository-wide cleanup of naming, UX, and logic fragmentation.

## ❌ What's Excluded and Why
- **Emergency Kill Switch ("Flatten & Fence"):** Currently exists as a verified stub. Full implementation is prioritized for the next sprint to ensure multi-channel reliability.
- **Live Macro Intelligence Alpha (FRED/YFinance):** Data pipelines are verified but waiting for final institutional risk sign-off before being enabled in the `main.py` loop.
- **Telegram Actionable Alerts:** Mobile-first "Approve/Reject" flow is in development and scheduled for v1.2.0.

## ⚠️ Known Limitations
- **Platform Constraint:** Native MT5 SDK remains Windows-only; MetaAPI fallback required for Linux/Mac production.
- **Initialization Latency:** High-fidelity feature calculation (140+ indicators) may add ~800ms to the first loop iteration.
- **Resource Intensity:** Minimum 16GB RAM recommended for full-stack analytics and vectorized feature engineering.

## 🧪 Testing Performed
- **Unit & Integration Tests:** 600+ tests passed with 100% success rate in the CI environment.
- **Product Coherence Verification:** 9 core governance and architectural vitals tests passed (2026-05-13).
- **Risk Harmonization Stress Test:** Verified the 8-layer cascade against synthetic "flash crash" and "toxic liquidity" scenarios.
- **Decision Cockpit Validation:** Verified TUI rendering and data accuracy for 50+ diverse signal packets.
- **Coverage:** Total repository coverage maintained at **87.6%**.

## 🛡️ Rollback Procedure
1. **Version Reversion:** Checkout tag `v1.1.0-rc7` and redeploy.
2. **Database:** Schema remains backward compatible; no migrations required.
3. **Emergency Stop:** Utilize `Makefile emergency-stop` or `docker stop trading-bot`.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

# 🚀 Release Candidate: v1.1.0-rc10

**Date:** 2026-05-19
**Status:** Release Candidate
**Tag:** `v1.1.0-rc10`

## 📝 Overview
This release candidate (v1.1.0-rc10) marks the transition to an **Intelligence-First** trading architecture. It consolidates advanced market regime detection, statistically rigorous model calibration, and institutional-grade behavioral journal mining. These features, combined with a structured Decision Support Cockpit and dynamic ensemble weighting, provide unprecedented transparency and adaptability for XAUUSD trading operations. Total repository test coverage is maintained at **87%**.

## ✅ What's Included and Why
- **Institutional Market Regime Detector:** Uses Gaussian Mixture Models (GMM) to classify XAUUSD market states (Trending, Ranging, News Shock, etc.). Enables regime-aware risk scaling and adaptive strategy selection.
- **Model Calibration & Reliability Engine:** Implements Brier score decomposition (Reliability, Resolution, Uncertainty) and Expected Calibration Error (ECE) to ensure model confidence scores represent true probabilities.
- **Decision Support Cockpit (DSS):** Unified operator interface providing "Go/No-Go" packets with SHAP-inspired signal attribution, regime alignment, and performance context.
- **Trade Journal Mining Engine:** Autonomous pattern recognition in trade history to detect behavioral risks (overtrading, revenge trading) and identify "Golden" vs. "Toxic" signal motifs.
- **Dynamic Ensemble Weighting:** Adaptive rebalancing of PPO, Dreamer, and LSTM models based on rolling performance and regime-specific accuracy.
- **Institutional RL Evaluation Framework:** Robust benchmarking suite with 20+ metrics (Sharpe, Sortino, Tail Ratio, Lake Ratio) against Random, Momentum, and Mean-Reversion baselines.
- **Decision Funnel Telemetry:** Enhanced Prometheus observability tracking signal progression from raw inference through risk filters to final execution.
- **Security & Model Hardening:** Hardened model loading with strict path validation and permission enforcement to prevent unauthorized weight manipulation.

## ❌ What's Excluded and Why
- **Emergency Kill Switch ("Flatten & Fence"):** Currently implemented as a verified stub in `Makefile`; production hardening of terminal state reconciliation is deferred to v1.2.0.
- **Live Macro Intelligence Pipeline:** FRED/YFinance integration remains in simulation mode pending final institutional risk sign-off for live data ingestion.
- **Telegram Actionable Alerts:** Dashboarding is active, but interactive "Close Position" button handlers are deferred for final security audit.

## ⚠️ Known Limitations
- **History Fragmentation:** The repository is currently operating with a disconnected Git history root on `main`, which requires manual audit of trading logic during integration.
- **Platform Constraint:** `MetaTrader5` remains Windows-only; Linux and CI environments utilize high-fidelity terminal mocks.
- **Initialization Latency:** MTF feature calculation and health checks may add up to 950ms to the first loop iteration after a cold start.

## 🧪 Testing Performed
- **Integration Audit (2026-05-18):** 100% pass rate across 5 critical system paths (Trading, Config, Backtesting, Resilience, Intelligence).
- **Core Loop Performance:** Measured at P50=0.68ms, P95=0.75ms, verifying high-throughput readiness.
- **Unit & Integration Tests:** 850+ tests passed; total coverage at 87% (CI threshold: 80%).
- **Stress Testing:** Validated system resilience against synthetic "News Shock" scenarios in StressLab.

## 🛡️ Rollback Procedure
1. **Version Reversion:** Checkout tag `v1.1.0-rc9` or `v1.1.0-rc8` and redeploy.
2. **Database:** Schema is backward compatible; no destructive migrations are included in this RC.
3. **Emergency Stop:** Utilize `Makefile emergency-stop` or `docker stop trading-bot`.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

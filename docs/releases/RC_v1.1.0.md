# 🚀 Release Candidate: v1.1.0-rc5

**Date:** 2026-05-07
**Status:** Release Candidate
**Tag:** `v1.1.0-rc5`

## 📝 Overview
This release candidate (v1.1.0-rc5) builds upon rc4 by integrating the first institutional-grade feature engineering pipeline and the foundational mapping for operational workflow simplification. Total repository test coverage has reached **87%**, exceeding the institutional release threshold.

## ✅ What's Included and Why
- **Institutional Feature Engineering Pipeline:** Vectorized pipeline computing 140+ features (RSI, MFI, MACD, ATR, Bollinger Bands, Candle Patterns, Volume Profiles). Includes multi-timeframe analysis (M1 to D1) with look-ahead bias prevention. Essential for high-fidelity model training and inference.
- **Workflow Simplification Mapping:** Comprehensive audit of 13 critical friction points (Setup, Backtesting, Emergency Stop, PR Triage). Establishes the roadmap for transitioning to one-command autonomous operations.
- **Enhanced Research Reporting System:** High-fidelity Jinja2-based reporting with institutional metrics (Tail Ratio, Common Sense Ratio, Gain-to-Pain Ratio, SQN).
- **Institutional Execution Quality Analytics:** Advanced tracking of slippage, latency, fill rates, and execution costs.
- **Enterprise Trade Logging:** SQLAlchemy 2.0-powered logging system with standardized audit trails.
- **Enterprise Health System:** Real-time monitoring of system vitals, including data freshness and connectivity status.
- **6-Layer Execution Filter Cascade:** Pre-trade gate system to block low-probability setups.

## ❌ What's Excluded and Why
- **Dreamer V3 World Model RL:** Integration remains in research to ensure zero impact on production stability.
- **Telegram Actionable Alerts:** Dashboarding logic is ready but "click-to-action" button handlers are deferred to v1.2.0 for final security review.
- **Live Macro Intelligence Pipeline:** FRED/YFinance data pipelines are pending final institutional risk sign-off for live integration.

## ⚠️ Known Limitations
- **Platform Constraint:** `MetaTrader5` remains Windows-only; system uses mocks for Linux-based research and CI.
- **Initialization Latency:** MTF feature calculation and health checks may add up to 850ms to the first loop iteration.
- **Memory Usage:** Vectorized analytics and large feature matrices require a minimum of 16GB RAM.

## 🧪 Testing Performed
- **Unit & Integration Tests:** 547 tests passed with 100% success rate.
- **Feature Pipeline Verification:** Verified 140+ indicators, normalization consistency, and look-ahead bias prevention.
- **Coverage:** Reached **87.0%** total repository coverage.
- **Institutional Scenarios:** Verified 15+ risk scenarios, including circuit breaker and regime-aware safety.

## 🛡️ Rollback Procedure
1. **Version Reversion:** Checkout tag `v1.1.0-rc4` or `v1.1.0-rc3` and redeploy.
2. **Database:** Schema is backward compatible; no `alembic` downgrade required.
3. **Emergency Stop:** Utilize `Makefile emergency-stop` or `docker stop trading-bot`.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

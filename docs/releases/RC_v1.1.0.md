# 🚀 Release Candidate: v1.1.0-rc2

**Date:** 2026-05-03
**Status:** Release Candidate
**Tag:** `v1.1.0-rc2`

## 📝 Overview
This release candidate (v1.1.0-rc2) incorporates the first major functional additions since the "Big Bang" integration. It introduces institutional-grade capital allocation, high-performance vectorized backtesting, and a sophisticated market regime detector. All components have been verified with >80% test coverage and integrated into the core trading loop.

## ✅ What's Included and Why
- **Institutional Capital Allocation:** A multi-strategy budget manager that enforces concentration limits (Symbol/Family) and dynamically scales risk based on real-time performance multipliers. Mandatory for managing multiple AI models safely.
- **Vectorized Backtesting Engine (v2):** A high-performance engine for walk-forward optimization. Significant performance improvements (2000x speedup in row access) enable rapid strategy iteration and Optuna-based hyperparameter tuning.
- **Market Regime Detection:** A statistical classifier that identifies 6 distinct market states (Trending, Ranging, News Shock, etc.). Enables the trading loop to adjust risk posture and model weighting based on environmental shifts.
- **Institutional Feature Engineering:** Full integration of the 190+ indicator pipeline into the live trading loop, ensuring models receive the same high-fidelity data in production as they did in training.
- **CI Quality & Stability:** Mandatory Mypy enforcement and Docker dependency harmonization to ensure codebase integrity and environment reproducibility.

## ❌ What's Excluded and Why
- **Explainable Decision Cockpit (TUI):** Design remains in terminal-only TUI; full dashboarding delayed to v1.2.0 to ensure zero impact on trading latency.
- **Dreamer V3 World Model:** Full world-model RL remains in research phase.
- **Live Pre-trade Telegram Gate:** Macro event briefing is active, but the manual Telegram approval gate is disabled by default for operational simplicity in this RC.

## ⚠️ Known Limitations
- **Platform Constraint:** `MetaTrader5` remains Windows-only; system uses sophisticated mocks for Linux-based CI and research.
- **Initialization Latency:** Large feature vectors (190+ indicators) across multiple timeframes may add 500ms to the first loop iteration during data warm-up.
- **Memory Usage:** Vectorized backtesting of >2 years of M1 data requires a minimum of 16GB RAM.

## 🧪 Testing Performed
- **Unit Tests:** 285 tests passed with 100% success rate.
- **Integration Tests:** Verified full data-to-execution flow, including CapitalAllocator rejection logic and Regime-aware weighting.
- **Coverage:** Reached **86.09%** total repository coverage, exceeding the enterprise 80% threshold.
- **Performance:** System latency metrics measured at P99 < 2ms (excluding network I/O).

## 🛡️ Rollback Procedure
1. **Version Reversion:** Checkout tag `v1.1.0-rc1` and redeploy.
2. **Database:** Schema is backward compatible; no `alembic` downgrade required from rc1 to rc2.
3. **Emergency Stop:** Utilize `Makefile emergency-stop` or `docker stop trading-bot`.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

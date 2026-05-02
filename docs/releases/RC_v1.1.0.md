# 🚀 Release Candidate: v1.1.0-rc1

**Date:** 2026-05-02
**Status:** Release Candidate
**Tag:** `v1.1.0-rc1`

## 📝 Overview
This release candidate (v1.1.0-rc1) represents a significant leap in the MT5 AI XAUUSD Trader's institutional capabilities. Following the "Big Bang" integration, the system now features a harmonized architecture, multi-layer execution filters, and an adaptive ensemble engine capable of regime-aware rebalancing.

## ✅ What's Included and Why
- **Institutional Feature Engineering:** Implements 190+ technical indicators and multi-timeframe analysis to provide models with high-fidelity market context.
- **Standardized Model Architecture:** Enforces a unified `BaseModel` interface and `Signal` object return format, enabling seamless model swapping and ensemble integration.
- **Enterprise Health Gate:** Mandatory startup validation ensures the bot only executes when MT5, Database, and Models are in a healthy state.
- **6-Layer Execution Filter:** A cascading validation gate (ATR, Trend Angle, EMA Sequence, Momentum, Session, Drawdown) to reduce false positives in high-noise regimes.
- **Adaptive Dynamic Ensemble:** Real-time weight rebalancing based on model performance (Sharpe/Calibration) and market regimes (e.g., News Shock).
- **Vectorized Backtesting Engine:** High-performance engine for rapid strategy validation and walk-forward research.
- **Enterprise Trade Logging:** SQLAlchemy 2.0-based logging with full migration support for institutional audit trails.
- **Monitoring & Observability:** Integrated Prometheus metrics and Telegram alerting for real-time operational visibility.

## ❌ What's Excluded and Why
- **Explainable Decision Cockpit (TUI):** Currently in scaffolding phase; excluded to maintain release stability. Targeted for v1.2.0.
- **Dreamer V3 Optimization:** Full world-model RL integration remains in research/future roadmap.
- **Pre-trade Briefing Active Gate:** Logic is implemented but Telegram confirmation flow is disabled by default until UI/UX tuning is completed.

## ⚠️ Known Limitations
- **Platform Constraint:** `MetaTrader5` library requires Windows for live execution; Linux environments must use the provided mocks for testing.
- **Memory Footprint:** Large-scale walk-forward optimization runs may require >16GB RAM for long historical periods.

## 🧪 Testing Performed
- **Unit Tests:** 100% pass rate across `src/core`, `src/models`, and `src/trading`.
- **Integration Tests:** Verified full data-to-execution flow, including circuit breaker and ensemble adaptation.
- **Environment Validation:** `scripts/doctor.py` and `scripts/validate_env.py` confirm 100% compliance with production specs.
- **Dependency Audit:** Reverted and pinned `requirements.txt` to verified institutional versions.

## 🛡️ Rollback Procedure
1. **Container Reversion:** Update `docker-compose.yml` to image tag `v1.0.0` and restart.
2. **Database Downgrade:** Execute `alembic downgrade -1` to revert recent schema changes.
3. **Emergency Stop:** Utilize the MT5 "Kill Switch" or `docker stop trading-bot` if catastrophic behavior is detected.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

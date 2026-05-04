# 🚀 Release Candidate: v1.1.0-rc3

**Date:** 2026-05-04
**Status:** Release Candidate
**Tag:** `v1.1.0-rc3`

## 📝 Overview
This release candidate (v1.1.0-rc3) builds upon the institutional foundations laid in rc2 by introducing enterprise-grade monitoring, a refined 9-layer execution filter, and a comprehensive audit trail. It also enhances the research suite with a sophisticated RL evaluation framework. This RC represents the "Stabilization & Observability" phase of the v1.1.0 cycle.

## ✅ What's Included and Why
- **9-Layer Execution Filter Cascade:** Upgraded from 6 layers to include Model Stability, Performance Floor, and Dynamic Confidence thresholds. This ensures signals are vetted not only against market conditions but also against the internal health and historical performance of the models.
- **Enterprise Monitoring & Alerting:** A centralized `Monitor` class integrating Prometheus for real-time metrics and Telegram for instant operator alerting. Provides visibility into equity, latency, and system health.
- **RL Evaluation Framework:** A research-grade evaluation suite for Reinforcement Learning agents, providing institutional metrics such as Sharpe ratio, turnover, and regime-aware performance decomposition.
- **Enterprise Audit Logging:** A persistent, singleton `AuditLogger` for managing system audit traces, ensuring all critical bot decisions and state changes are traceable for compliance.
- **Workflow Simplification:** Automated operational friction mapping and detailed automation designs in the `WORKFLOW_SIMPLIFICATION_LOG.md`.

## ❌ What's Excluded and Why
- **Live Macro Intelligence:** Macro event data ingestion is implemented, but the live feedback loop into execution is remains in "observation mode" to prevent unintended trade blocking until further validation.
- **What-If Sensitivity Panel:** Pre-trade stress testing is available in research (`StressLab`), but integration into the live Decision Cockpit TUI is deferred to the next RC.

## ⚠️ Known Limitations
- **Memory Overhead:** The inclusion of comprehensive monitoring and audit logging increases memory footprint by ~100MB.
- **Numpy Compatibility:** Requires `numpy < 2.0` (pinned to 1.26.4) to maintain compatibility with compiled TA-Lib and Torch modules in the current environment. Unused `pandas-ta` was removed to resolve Python 3.12 version conflicts.

## 🧪 Testing Performed
- **Unit Tests:** 76/76 targeted tests passed for new core components.
- **Integration Tests:** Verified singleton behavior of AuditLogger and successful Prometheus metric export.
- **Coverage:** Maintained **>80%** repository coverage across all core modules.

## 🛡️ Rollback Procedure
1. **Version Reversion:** Checkout tag `v1.1.0-rc2` and redeploy.
2. **Database:** Audit logs are stored in a separate `audit.db` by default; no schema migration required for the primary trade database.
3. **Emergency Stop:** Utilize `Makefile emergency-stop` or `docker stop trading-bot`.

---
*Prepared by Jules05 (yxynoty) — Autonomous Product Steward.*

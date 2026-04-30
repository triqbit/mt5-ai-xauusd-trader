# 🚀 Release Candidate: v1.0.0-rc3

## 📅 Date: 2026-04-30
## 👤 Author: Jules05

---

## 🏛️ Executive Summary
This release candidate (v1.0.0-rc3) achieves critical architecture harmonization and introduces institutional-grade reliability features. It resolves logic fragmentation by removing stale abstractions, integrates a comprehensive startup health gate, and provides standardized operational runbooks. Additionally, it hardens system security by updating core ML dependencies to non-vulnerable versions.

---

## ✅ What's Included

### 1. Architecture Harmonization
- **Source**: `origin/fix/jules05-harmonization-6949952969784913660`
- **Rationale**: Consolidates component initialization in `main.py` and standardizes the `MT5Connector` interface. Resolves multi-agent logic duplication.
- **Cleanup**: Removed stale `OrderManager` and `PortfolioManager` modules.
- **Verification**: `tests/test_harmonization.py` passing (2/2).

### 2. Enterprise Health Gate
- **Source**: `origin/atlas/health-monitoring-gate-16243718335848234220`
- **Rationale**: Implements mandatory startup probes for disk space, database connectivity, MT5 terminal status, and model availability. Prevents bot execution in degraded environments.
- **Verification**: `tests/test_health.py` passing (10/10).

### 3. Security & Dependency Hardening
- **Source**: `origin/dependency-management-and-security-16960673108976038504`
- **Rationale**: Updated `torch` (2.11.0), `torchvision` (0.26.0), and `stable-baselines3` (2.8.0) to resolve critical security vulnerabilities (PYSEC-2025-41, GHSA-3749-ghw9-m3mg). Standardized on `python-telegram-bot`.
- **Verification**: Local verification of dependency safety and full test suite execution.

### 4. Operational Runbooks
- **Source**: `origin/add-operational-runbooks-1241299720848641225`
- **Rationale**: Introduces 7 formal runbooks covering CI recovery, connection outages, circuit breakers, and secret rotation. Essential for enterprise-grade operations.
- **Verification**: Documentation audit (verified files in `docs/runbooks/`).

### 5. RL Observation Optimization
- **Source**: `origin/bolt/optimize-gym-env-observations-16744521746686060435`
- **Rationale**: Performance-optimized vectorized observation generation in `TradingEnv`. Reduces latency in the inference loop.
- **Verification**: Structural verification in `src/environment/gym_env.py`.

---

## ❌ What's Excluded (Escalated for Risk)

The following branches touch high-risk trading logic or risk parameters and remain in the escalation queue for manual review:

| Branch | Reason for Exclusion |
| :--- | :--- |
| `origin/jules02-hardened-risk-controls-...` | Modifies core risk limits (daily trade limits, consecutive losses). |
| `origin/feat/event-intelligence-...` | Introduces live signal filtering based on macro events. |
| `origin/feature/trade-logging-system-...` | High-impact database schema changes. |

---

## 🔍 Testing Performed
1. **Core Unit Testing**: Executed 25 tests with 100% pass rate in the sandbox.
2. **Harmonization Check**: Verified RiskManager initialization with both TradeLogger and Monitor.
3. **Health Gate Validation**: Verified that all probes (Disk, DB, MT5, Model) return correct `HealthStatus`.
4. **Security Audit**: Verified non-vulnerable versions of core ML libraries are pinned.
5. **Linting**: Verified zero regressions using `ruff check`.

---

## ⏪ Rollback Procedure
1. **Codebase**: `git checkout release/v1.0.0-rc2` and redeploy.
2. **Infrastructure**: Revert Docker image to tag `v1.0.0-rc2`.
3. **Emergency**: Use `docs/runbooks/05-failed-deployment-rollback.md` for detailed instructions.

---

## ⚠️ Known Limitations
- Health Gate requires valid `MT5_USER` and `MT5_PASSWORD` for MT5 connectivity probes (stubbed in dev).
- TA-Lib C library is required for feature engineering modules (integrated in RC2).

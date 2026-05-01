# Release Candidate v1.1.0

## 🎯 Release Summary
This release candidate (v1.1.0) establishes the institutional-grade foundation for the MT5 AI/ML XAUUSD Trader. It consolidates foundational CI fixes, enterprise scaffolding, production-ready logic, and comprehensive documentation from Jules01-04.

## ✅ What's Included and Why
- **CI Stability & Import Fixes** (`origin/fix-ci-and-imports-...`): Ensures a clean development environment and resolves previous build failures.
- **Enterprise Scaffolding** (`origin/scaffold-enterprise-src-...`): Establishes a scalable directory structure and core module interfaces.
- **Production-Ready Logic** (`origin/atlas-production-ready-logic-...`): Implements robust entrypoint validation and core risk management logic.
- **Enterprise Governance** (`origin/feat/enterprise-governance-...`): Adds contribution controls, issue templates, and CODEOWNERS.
- **Versioning & Changelog Automation** (`origin/setup-versioning-automation-...`): Implements SemVer and automated changelog generation.
- **Technical Documentation Infrastructure** (`origin/documentation-improvements-...`): MkDocs setup with API references and architectural guides.
- **Institutional Monitoring** (`origin/implement-monitoring-system-...`): Real-time telemetry and alerting system.
- **Formal Acceptance Criteria** (`origin/jules05/acceptance-criteria-...`): Codified quality gates for core framework components.
- **Strategic Product Roadmap** (`origin/jules05-feature-roadmap-...`): Defined trajectory for future development phases.
- **Workflow Simplification** (`origin/workflow-simplification-ops-...`): Mapping and automation of manual operational friction points.
- **Explainable Regime-Aware Cockpit** (`origin/jules05/differentiation-cockpit-...`): Unique institutional feature for model transparency.
- **Strict Data Validation (Pydantic v2)** (`origin/feat/strict-data-validation-...`): Robust schema enforcement across market data and signals.
- **Advanced Feature Engineering** (`origin/feature-engineering-module-...`): Core pipeline for technical and statistical indicators.
- **Model Calibration & Temperature Scaling** (`origin/feat/model-calibration-...`): Statistical alignment of model confidence scores.

## ❌ What's Excluded and Why
- **Advanced Risk Management** (`origin/advanced-risk-management-...`): Excluded due to high risk; requires manual human sign-off on trade execution logic.
- **Capital Allocator** (`origin/feat/capital-allocator-...`): Strategic research work still in validation.
- **Execution Filter Cascade** (`origin/feature/execution-filter-cascade-...`): Complex gating logic that requires further stress testing in demo environments.
- **Experimental ML Models**: Only stable stubs and the core ensemble framework are included.

## ⚠️ Known Limitations
- Integration with MetaTrader 5 terminal requires Windows environment or MetaAPI cloud bridge.
- ML models (PPO/LSTM) are currently stubs and require training on historical XAUUSD data.
- Live trading is gated by `MODE` environment variable; default is `demo`.

## 🧪 Testing Performed
- Unit tests for core configuration, monitoring, and trade logging.
- Integration tests for MT5 connectivity and risk engine validation.
- Linting and formatting checks (Ruff, Mypy).
- Manual verification of documentation integrity.

## 🔄 Rollback Procedure
1. **Infrastructure**: Revert to previous stable commit on `main` branch.
2. **Configuration**: Roll back `.env` changes to previous known-good state.
3. **Database**: If migrations were applied, run `alembic downgrade -1`.
4. **Docker**: Re-deploy using the previous image tag (e.g., `v1.0.0`).

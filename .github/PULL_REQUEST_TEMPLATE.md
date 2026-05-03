## Description
Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Type of change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] 🚀 New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] ⚡ Performance improvement
- [ ] 🛡️ Security / Governance update

## 💥 Breaking Changes & Compatibility
- [ ] Does this PR introduce breaking changes?
- [ ] If yes, describe the impact and migration path.
- [ ] Backward compatibility has been verified.

## 🛡️ Security & Risk Impact
- [ ] Does this PR touch any financial/trading logic? (If so, explain the risk mitigation)
- [ ] Does this PR handle sensitive credentials or secrets? (Verified they are not logged/exposed)
- [ ] Any new dependencies added? (Verified license compliance)
- [ ] Any potential for recursive loops or resource exhaustion?

## 🔄 Rollback Strategy
- [ ] What is the plan if this deployment fails in production?
- [ ] Are database migrations reversible? (Verified via `verify_migrations.py`)
- [ ] Can the system be rolled back without data loss?

## 📊 Observability (Logs/Metrics)
- [ ] Are critical operational events logged?
- [ ] Have you added or updated Prometheus metrics?
- [ ] Is there an audit trail record for significant state changes?

## ⚡ Performance Benchmarks
- [ ] Performance impact assessed (Inference latency, memory footprint, etc.)
- [ ] Backtest results provided (if applicable)

## 📋 Checklist
- [ ] My code follows the style guidelines of this project (Ruff/Black).
- [ ] I have performed a self-review of my own code.
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] I have made corresponding changes to the documentation.
- [ ] My changes generate no new warnings.
- [ ] I have added tests that prove my fix is effective or that my feature works.
- [ ] New and existing unit tests pass locally with my changes.
- [ ] Risk limits and circuit breakers have been verified (if applicable).
- [ ] All CI/CD gates are expected to pass (Tests, Security, Linting).

## 🧪 Verification Results
Please provide evidence of testing and verification (e.g., test output, screenshots, backtest results).

### Tests Run
- [ ] `python -m pytest tests/` (Mandatory: All tests must pass)
- [ ] `mypy src/` (Mandatory: Zero type errors)
- [ ] `ruff check .` (Mandatory: Zero linting errors)

### Coverage Report
- [ ] **Minimum required coverage: 85%** (Aligned with Excellence Blueprint)
- Current coverage: [Insert % here]

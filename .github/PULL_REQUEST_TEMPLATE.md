## 📝 Description
Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## 🏗️ Type of change
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
- [ ] Any new dependencies added? (Verified license compliance via `docs/LICENSE_COMPLIANCE.md`)
- [ ] Any potential for recursive loops or resource exhaustion?

## ⚖️ Governance & Compliance
- [ ] My code follows the style guidelines of this project (Ruff/Black).
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] I have made corresponding changes to the documentation in `docs/`.
- [ ] All new dependencies are listed in the appropriate `requirements*.txt` file.
- [ ] License compliance verified for all new packages.

## 🔄 Rollback Strategy
- [ ] What is the plan if this deployment fails in production?
- [ ] Are database migrations reversible? (Verified via `verify_migrations.py`)
- [ ] Can the system be rolled back without data loss?

## 📊 Observability (Logs/Metrics)
- [ ] Are critical operational events logged using `structlog`?
- [ ] Have you added or updated Prometheus metrics?
- [ ] Is there an audit trail record for significant state changes?

## ⚡ Performance Benchmarks
- [ ] Performance impact assessed (Inference latency, memory footprint, etc.)
- [ ] Backtest results provided (if applicable)

## 🧪 Verification Results
Please provide evidence of testing and verification.

### Mandatory Quality Gates
- [ ] `python3 scripts/doctor.py` (Environment check passed)
- [ ] `python3 -m pytest tests/` (All tests passed)
- [ ] `mypy src/` (Zero type errors)
- [ ] `ruff check .` (Zero linting errors)
- [ ] `pip-audit` (Zero known vulnerabilities)
- [ ] **Code Coverage: ≥ 85%** (Statement coverage verified)
- [ ] **Documentation updated** (Reflecting all source changes)
- [ ] **Backward compatibility verified** (No unintended breaking changes)

### Testing Evidence
- [ ] Test output attached/pasted below.
- [ ] Screenshots of frontend changes (if applicable).
- [ ] Backtest report (for trading logic changes).

---
*By submitting this PR, I confirm that my contribution is made under the terms of the project's MIT License.*

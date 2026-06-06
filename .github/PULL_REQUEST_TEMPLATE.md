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

## 🛡️ Contribution Safety Checklist
Before submitting, please categorize your PR based on the [Contribution Map](docs/CONTRIBUTION_MAP.md):

- [ ] **Safety Zone:** I have verified my PR falls into:
  - [ ] 🟢 **Safe Zone** (docs, tests, scripts)
  - [ ] 🟡 **Utility Zone** (utils, analytics)
  - [ ] 🔴 **Sensitive Zone** (trading, models, core) - *Requires Multi-Signature Approval*
- [ ] **History Alignment:** I have rebased my branch onto the latest `main` graft.
- [ ] **Rebase Check:** `git fetch origin main && git rebase origin/main` (Command executed and passed)

## ✅ Mandatory Quality Gates
These checks are required before the PR can be merged:
- [ ] **Tests Passed:** `python3 -m pytest tests/` (All tests passed)
- [ ] **Code Coverage:** Statement coverage ≥ 85% (Verified via `pytest-cov`)
- [ ] **Security Scan:** `pip-audit` or `trivy` shows zero known vulnerabilities
- [ ] **Documentation:** Updated `docs/` to reflect all source changes
- [ ] **Type Safety:** `mypy src/` (Zero type errors)
- [ ] **Linting:** `ruff check .` (Zero linting errors)

## 🏗️ Technical Checklist
- [ ] **Testing Done:** Evidence of local or environment testing provided below.
- [ ] **Docs Updated:** Any change in logic or config is reflected in documentation.
- [ ] **Backward Compatibility Verified:** Verified that this change does not break existing deployments.
- [ ] **Rollback Strategy:** Reversion path identified for database or config changes.

## 💥 Breaking Changes & Compatibility
- [ ] Does this PR introduce breaking changes?
- [ ] If yes, describe the impact and migration path.

## 🛡️ Security & Risk Impact
- [ ] Does this PR touch any financial/trading logic? (If so, explain the risk mitigation)
- [ ] Does this PR handle sensitive credentials or secrets? (Verified they are not logged/exposed)
- [ ] Any new dependencies added? (Verified license compliance via `docs/LICENSE_COMPLIANCE.md`)

## 📊 Observability (Logs/Metrics)
- [ ] Are critical operational events logged using `structlog`?
- [ ] Have you added or updated Prometheus metrics?
- [ ] Is there an audit trail record for significant state changes?

## 🧪 Verification Results
Please provide explicit evidence of testing and verification.

### Testing Evidence
- [ ] **Test Output:** Attached or pasted below.
- [ ] **Screenshots/Logs:** Visual evidence of successful execution.
- [ ] **Backtest Results:** Required for any changes to trading or model logic.
- [ ] **Manual Verification:** Steps taken to verify the change in a live/demo environment.

---
*By submitting this PR, I confirm that my contribution is made under the terms of the project's MIT License.*

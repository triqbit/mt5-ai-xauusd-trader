## Description
Briefly describe the changes introduced by this PR. Include motivation and context.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Configuration change (update to environment variables or settings)
- [ ] Documentation update
- [ ] CI/CD or Tooling improvement

## Mandatory Checklist
*All items must be checked before a PR can be merged.*

### 🛠️ Technical Quality
- [ ] Code follows the project's style guidelines (Ruff/Mypy pass locally).
- [ ] I have performed a self-review of my own code.
- [ ] New and existing unit tests pass locally with my changes.
- [ ] Code coverage is maintained or improved (Target: >25% for PR, >80% for Release).
- [ ] Backward compatibility has been verified (no breaking changes without migration).

### 📖 Documentation & Traceability
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] I have made corresponding changes to the documentation (README, ENTERPRISE_STANDARDS, etc.).
- [ ] Any new environment variables are documented in `.env.example`.
- [ ] Related issue(s) are linked (e.g., `Fixes #123`).

### 🛡️ Security & Compliance
- [ ] No secrets or sensitive data (API keys, passwords) are committed.
- [ ] Third-party dependencies are CVE-free (`pip-audit` / `trivy` scan).
- [ ] License compliance verified for any new dependencies.

### 🚀 Performance & Reliability
- [ ] Performance impact has been assessed (no significant regression in latency/memory).
- [ ] Error handling is robust and includes proper logging.
- [ ] (If applicable) DB migrations are reversible and follow naming standards.

## Verification
Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce.

**Test Configuration:**
*   Environment: [e.g. Local, Docker, CI]
*   Python Version: [e.g. 3.11]
*   MT5 Mode: [e.g. Demo, Mock]

---
*By submitting this PR, I agree to abide by the repository's Contribution Governance standards.*

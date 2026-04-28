# Pre-Production Acceptance Checklist (GATE)

This checklist defines the mandatory requirements that must be met and signed off before any release is promoted to production.

## 1. 🛡️ Quality & Coverage Gates
- [ ] **Unit Test Pass Rate:** 100% of all tests in `tests/` must pass.
- [ ] **Code Coverage:** Minimum **80%** total line coverage (enforced for production releases).
- [ ] **Static Analysis:** Zero violations in `ruff check` and `ruff format --check`.
- [ ] **Type Safety:** `mypy` must pass with zero errors on `src/`.

## 2. 🔐 Security & Compliance Gates
- [ ] **Dependency Audit:** `pip-audit` must report zero known vulnerabilities in `requirements-ci.txt`.
- [ ] **Secret Scanning:** No secrets, API keys, or private tokens detected in codebase.
- [ ] **License Audit:** All dependencies must comply with the License Policy (MIT, Apache 2.0, etc.).
- [ ] **Docker Scan:** Container image must be scanned for OS-level vulnerabilities (Trivy/Snyk).

## 3. ⚙️ Configuration & Environment Gates
- [ ] **Environment Template:** `.env.example` is updated with all required variables for the new version.
- [ ] **Health Check:** Startup Health Gate (`main.py`) verified in a staging/dry-run environment.
- [ ] **Database Migrations:** All migrations in `migrations/versions/` are tested and reversible.

## 4. 📦 Artifact & Documentation Gates
- [ ] **Semantic Versioning:** Version bumped correctly in `src/__init__.py` and `pyproject.toml`.
- [ ] **Changelog:** `CHANGELOG.md` updated with all changes since the last release.
- [ ] **Runbooks:** Any new features have corresponding operational runbooks in `docs/runbooks/`.
- [ ] **Integrity:** Release artifacts have valid SHA256 checksums generated.

## 5. 🚀 Final Sign-off
- **Release Engineer (Jules03):** ____________________ Date: __________
- **Lead Developer (Jules01):** ____________________ Date: __________

---
**Note:** Failure to meet any of the above criteria will result in an automatic deployment block.

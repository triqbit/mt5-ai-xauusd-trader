# PHASE 1: CI/CD & Code Quality Roadmap
**MT5 AI/ML Trading Bot - Enterprise-Grade Transformation**

**Status:** 🔄 In Progress | **Target Completion:** Week 1-2 | **Priority:** 🔴 CRITICAL

---

## 📊 Current Status (April 18, 2026)

### ✅ Completed Tasks
1. **Fixed unused imports** in `src/trading/risk_manager.py`
   - Removed `Optional` from typing imports (commit: d714322)
   - Removed unused `List` import (commit: de00d2c)

2. **Organized import structure** 
   - Added blank lines between import sections (commit: 57cffc0)
   - Separated stdlib from local imports

### 🔄 In Progress
3. **Import sorting refinement** (I001 error)
   - Issue: Ruff still detecting un-sorted imports
   - Next: Configure ruff to auto-fix import order

### ⏳ Remaining Critical Tasks
4. Configure ruff import sorting in `pyproject.toml`
5. Create `.pre-commit-config.yaml` for automated checks
6. Enable GitHub Dependabot for dependency scanning
7. Enable CodeQL security scanning  
8. Add branch protection rules
9. Configure automated testing
10. Set up code coverage reporting

---

## 🎯 Phase 1 Objectives

**PRIMARY GOAL:** Get CI/CD pipeline passing ✅ (100% green builds)

**SUCCESS METRICS:**
- ✅ All GitHub Actions workflows passing
- ✅ Zero linting errors (ruff check)
- ✅ Zero type errors (mypy --strict)
- ✅ Test coverage >80%
- ✅ Security scanning enabled
- ✅ Automated dependency updates

---

## 📋 Detailed Action Plan

### **STEP 1: Fix Remaining Lint Errors** 🔴 CRITICAL
**Time:** 1-2 hours | **Owner:** Dev Team

#### Tasks:
- [ ] Configure ruff import sorting in `pyproject.toml`
  ```toml
  [tool.ruff]
  select = ["E", "F", "I"]
  fix = true
  
  [tool.ruff.isort]
  known-first-party = ["src"]
  ```
- [ ] Run `ruff check --fix src/` to auto-fix imports
- [ ] Verify all files pass: `ruff check src/ tests/`
- [ ] Commit: `fix: Configure ruff and resolve all linting errors`

#### Expected Outcome:
✅ CI "Code Quality" job passes
✅ Zero lint warnings

---

### **STEP 2: Add Pre-Commit Hooks** 🟡 HIGH
**Time:** 30 minutes | **Owner:** Dev Team

#### Tasks:
- [ ] Create `.pre-commit-config.yaml`
  ```yaml
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.3.0
      hooks:
        - id: ruff
          args: [--fix]
        - id: ruff-format
    
    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v4.5.0
      hooks:
        - id: trailing-whitespace
        - id: end-of-file-fixer
        - id: check-yaml
        - id: check-added-large-files
        - id: check-merge-conflict
  ```
- [ ] Install: `pip install pre-commit && pre-commit install`
- [ ] Test: `pre-commit run --all-files`
- [ ] Commit: `chore: Add pre-commit hooks for code quality`

#### Expected Outcome:
✅ Hooks run automatically on every commit
✅ Code quality enforced before push

---

### **STEP 3: Enhanced Ruff Configuration** 🟡 HIGH  
**Time:** 1 hour | **Owner:** Dev Team

#### Tasks:
- [ ] Update `pyproject.toml` with comprehensive ruff rules
  ```toml
  [tool.ruff]
  target-version = "py310"
  line-length = 100
  select = [
      "E",   # pycodestyle errors
      "F",   # pyflakes
      "I",   # isort
      "N",   # pep8-naming
      "UP",  # pyupgrade
      "B",   # flake8-bugbear
      "C4",  # flake8-comprehensions
      "SIM", # flake8-simplify
  ]
  
  [tool.ruff.per-file-ignores]
  "__init__.py" = ["F401"]  # Allow unused imports in __init__
  ```
- [ ] Run and fix: `ruff check --fix src/ tests/`
- [ ] Commit: `config: Add comprehensive ruff configuration`

---

### **STEP 4: Type Checking with mypy** 🟢 MEDIUM
**Time:** 2-3 hours | **Owner:** Dev Team

#### Tasks:
- [ ] Add mypy to `requirements.txt`
- [ ] Configure in `pyproject.toml`:
  ```toml
  [tool.mypy]
  python_version = "3.10"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true
  ```
- [ ] Add mypy to CI workflow (`.github/workflows/ci.yml`)
- [ ] Fix type errors incrementally
- [ ] Commit: `chore: Add mypy type checking`

---

### **STEP 5: Test Coverage** 🟢 MEDIUM
**Time:** 3-4 hours | **Owner:** Dev Team

#### Tasks:
- [ ] Install: `pip install pytest pytest-cov pytest-mock`
- [ ] Add more unit tests in `tests/`
  - `tests/test_risk_manager.py`
  - `tests/test_mt5_connector.py`
  - `tests/test_config.py` (already exists)
- [ ] Configure coverage in `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "--cov=src --cov-report=html --cov-report=term-missing"
  ```
- [ ] Add coverage to CI
- [ ] Set minimum coverage: 80%
- [ ] Commit: `test: Increase coverage to 80%+`

#### Expected Outcome:
✅ >80% test coverage
✅ Coverage reports in CI

---

### **STEP 6: Enable Security Features** 🔴 CRITICAL
**Time:** 30 minutes | **Owner:** Repo Admin

#### Tasks:
- [ ] **Enable Dependabot**
  - Settings → Security → Enable Dependabot alerts
  - Settings → Security → Enable Dependabot security updates
  - Create `.github/dependabot.yml`:
    ```yaml
    version: 2
    updates:
      - package-ecosystem: "pip"
        directory: "/"
        schedule:
          interval: "weekly"
        open-pull-requests-limit: 10
    ```

- [ ] **Enable CodeQL Code Scanning**
  - Security → Code scanning → Set up CodeQL
  - Select Python analysis
  - Commit workflow: `.github/workflows/codeql.yml`

- [ ] **Create SECURITY.md**
  ```markdown
  # Security Policy
  
  ## Reporting Vulnerabilities
  Email: security@triqbit.com
  Response time: 48 hours
  ```

#### Expected Outcome:
✅ Automated vulnerability scanning
✅ Weekly dependency updates
✅ Security policy published

---

### **STEP 7: Branch Protection Rules** 🔴 CRITICAL
**Time:** 15 minutes | **Owner:** Repo Admin

#### Tasks:
- [ ] Navigate to Settings → Branches → Add rule
- [ ] Branch name pattern: `main`
- [ ] Enable:
  - ✅ Require pull request before merging
  - ✅ Require status checks to pass
    - ✅ Code Quality
    - ✅ Tests  
    - ✅ Docker Build
  - ✅ Require conversation resolution
  - ✅ Do not allow bypassing

#### Expected Outcome:
✅ No direct pushes to main
✅ All code reviewed before merge
✅ CI must pass before merge

---

### **STEP 8: Documentation Updates** 🟢 MEDIUM
**Time:** 2 hours | **Owner:** Dev Team

#### Tasks:
- [ ] Create `CONTRIBUTING.md`
  - Development setup
  - Code style guide
  - Pull request process
  - Testing requirements

- [ ] Update `README.md`
  - Add CI status badges
  - Add coverage badge
  - Add security scan badge

- [ ] Create `CODE_OF_CONDUCT.md`

---

## 🚀 Quick Start Commands

### Fix Import Issues NOW:
```bash
# 1. Install/update ruff
pip install --upgrade ruff

# 2. Auto-fix all import issues
ruff check --select I --fix src/ tests/

# 3. Verify all checks pass  
ruff check src/ tests/

# 4. Commit
git add -A
git commit -m "fix: Resolve all ruff import sorting errors (I001)"
git push
```

### Set Up Pre-Commit Hooks:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Run All Quality Checks:
```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Tests with coverage
pytest --cov=src --cov-report=term-missing

# Security scan
bandit -r src/
```

---

## 📈 Success Criteria

### Week 1 Goals (Days 1-7):
- ✅ All CI builds passing (green)
- ✅ Pre-commit hooks configured
- ✅ Ruff + mypy configured
- ✅ Basic tests >50% coverage
- ✅ Security scanning enabled

### Week 2 Goals (Days 8-14):
- ✅ Test coverage >80%
- ✅ Branch protection active
- ✅ Documentation complete
- ✅ First external contribution accepted

---

## 🔄 Continuous Improvement

After Phase 1 completion:
1. **Phase 2:** Architecture & Missing Features (Weeks 3-6)
2. **Phase 3:** Production Readiness (Weeks 7-8)
3. **Phase 4:** AI/ML Implementation (Weeks 9-12)

See `EXCELLENCE_BLUEPRINT.md` for full roadmap.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/triqbit/mt5-ai-xauusd-trader/issues)
- **Discussions:** [GitHub Discussions](https://github.com/triqbit/mt5-ai-xauusd-trader/discussions)
- **Email:** dev@triqbit.com

---

**Last Updated:** April 18, 2026  
**Maintained By:** @triqbit  
**Status:** 🔄 Active Development

# 🚀 Your First Real Contribution

Welcome to the MT5 AI/ML Trading Bot project! We are thrilled to have you. This guide provides a low-risk, high-impact path to your first Pull Request, specifically designed to help you navigate our current high-turbulence development environment.

## 🌪️ Turbulence Survival Guide

Before you start, be aware of two unique factors in this repository:

1.  **History Grafting:** The `main` branch is updated daily via monolithic "grafts" (total repository swaps). This means standard Git history is often unavailable on `main`.
2.  **Mandatory Rebase:** Because `main` resets daily, your feature branch **must** be rebased onto the latest `main` commit before submission.
3.  **Environment Stability:** If `make bootstrap` fails, check `docs/status/PROJECT_HEALTH.md` for known dependency conflicts.

---

## 🎯 Your Mission: Reduce the "Lint Debt"

The repository currently has a significant amount of "lint debt" (over 4,400 issues), primarily in the `tests/` directory. Since `tests/` is a defined **Safe Zone**, this is the perfect place for a first contribution.

### Step 1: Prepare Your Environment

```bash
# 1. Update your local main
git checkout main
git pull origin main

# 2. Install development tools
pip install ".[dev]"

# 3. Create a cleanup branch
git checkout -b refactor/cleanup-test-lint
```

### Step 2: Identify Targets

Run the linter and filter for the `tests/` directory:
```bash
make lint | grep "tests/"
```

You will likely see many errors like `F401 (unused-import)` or `F841 (unused-variable)`.

### Step 3: Implement Fixes

Choose a single test file (e.g., `tests/test_performance.py`) and fix the identified lint issues.

**Pro Tip:** Use `ruff` to automatically fix what it can:
```bash
python -m ruff check tests/test_performance.py --fix
```

### Step 4: Verify Your Changes

Ensure the linter is happy with that specific file:
```bash
python -m ruff check tests/test_performance.py
```

**CRITICAL:** Ensure you haven't broken the tests themselves!
```bash
make test
```
*(Note: If `make test` fails globally due to environment issues, ensure it at least doesn't fail more than it did before your changes.)*

### Step 5: Submit for Review

1.  **Commit with Conventional Commits:** `test: resolve lint issues in tests/test_performance.py`
2.  **Rebase:** `git rebase main`
3.  **Push and PR:** Open a PR and tag **Jules06 (@maintainer-quality)** for review.

---

## 🛡️ Safety Boundaries

As a reminder from the [Contribution Map](./CONTRIBUTION_MAP.md):

-   ✅ **DO** contribute to `docs/`, `tests/`, and `scripts/`.
-   ❌ **DO NOT** modify `src/trading/`, `src/models/`, or `src/core/` in your first PR. These require multi-signature approval and extensive evidence.

## 🆘 Need Help?

If you get stuck on a dependency conflict or a Git rebase issue:
1.  Check [docs/status/PROJECT_HEALTH.md](./status/PROJECT_HEALTH.md).
2.  Open a Discussion on GitHub.
3.  Tag a maintainer in your Draft PR.

Thank you for helping us make this system more enterprise-grade!

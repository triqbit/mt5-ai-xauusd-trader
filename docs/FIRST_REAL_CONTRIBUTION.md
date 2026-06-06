# 🚀 Your First Real Contribution

Welcome to the MT5 AI/ML Trading Bot project! We are thrilled to have you. This guide provides a low-risk, high-impact path to your first Pull Request, specifically designed to help you navigate our current high-turbulence development environment.

## 🌪️ Turbulence Survival Guide

Before you start, be aware of two unique factors in this repository:

1.  **History Grafting:** The `main` branch is updated daily via monolithic "grafts" (total repository swaps). This means standard Git history is often unavailable on `main`.
2.  **Mandatory Rebase:** Because `main` resets daily, your feature branch **must** be rebased onto the latest `main` commit before submission.
3.  **Environment Stability:** If `make bootstrap` fails, check `docs/status/PROJECT_HEALTH.md` for known dependency conflicts.

---

## 🎯 Your Mission: Enhance System Diagnostics

As an institutional-grade system, our "Time to First Success" is critical. Your mission is to improve the `scripts/doctor.py` tool by adding a new diagnostic check or improving an existing one. This is a high-impact, low-risk way to help every developer who joins after you.

### Step 1: Prepare Your Environment

```bash
# 1. Update your local main
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feature/doctor-enhancement
```

### Step 2: Identify a Diagnostic Gap

Run the doctor script and look for missing checks that would be helpful for a new user:
```bash
make doctor
```

**Ideas for first contributions:**
- Add a check for available disk space (important for `trades.db`).
- Add a check for the existence of the `data/` directory.
- Improve the error message for a failing database connectivity check.
- Add a check to verify that `docker` is installed if the user is in a Linux environment.

### Step 3: Implement the Check

Open `scripts/doctor.py` and implement a new `DiagnosticCheck`. Use the existing functions like `check_python_version()` as a template.

### Step 4: Verify Your Changes

Run the doctor script again to see your new check in action:
```bash
make doctor
```

### Step 5: Submit for Review

1.  **Commit with Conventional Commits:** `feat: add disk space check to doctor diagnostics`
2.  **Final Rebase (Critical):** Always rebase just before pushing to ensure you are on the latest graft:
    ```bash
    git fetch origin main
    git rebase origin/main
    ```
3.  **Push and PR:** Open a PR and tag **Jules06 (@qufuwan)** for review.

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

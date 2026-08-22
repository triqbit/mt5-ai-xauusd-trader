# 🚀 Your First Real Contribution

Welcome to the MT5 AI/ML Trading Bot project! We are thrilled to have you. This guide provides a low-risk, high-impact path to your first Pull Request, specifically designed to help you navigate our clean, automated development environment.

---

## 🟢 Clean Development Environment

To begin contributing confidently, know that our repo prioritizes robust and automated software practices:

1. **Intact Linear History:** Our repository maintains a completely linear, intact, and stable Git history (1,260+ commits tracing back to the root). You can confidently rely on standard Git workflows.
2. **Automated Syncing:** Keep your branch aligned with the latest `main` commit using `make resync` (or standard `git rebase`).
3. **CI Status:** CI is fully **🟢 PASSING**. All formatting, linting, and tests execute cleanly.
4. **Environment Stability:** Run `make bootstrap` to initialize your local python virtual environment, and verify system setup via `make doctor`.

---

## 🚦 PR Title & Commit Standards (Crucial CI Gate)

Our repository enforces a strict semantic pull request check using the `amannn/action-semantic-pull-request` checker.

> [!WARNING]
> **Do NOT use the "DX:" prefix in your Pull Request Title or commit messages.**
> Even though our developer experience team uses "DX" internally, the CI checker **rejects** the `DX:` prefix.
>
> **Allowed Semantic Prefixes:**
> - `docs:` for documentation and onboarding enhancements (e.g., `docs: improve developer onboarding guide`)
> - `chore:` for developer tool scripts and auxiliary tasks (e.g., `chore: add directory validation check to doctor`)
> - `test:` for writing or updating unit tests (e.g., `test: add unit tests for doctor checks`)
> - `fix:` for fixing developer experience utilities (e.g., `fix: resolve doctor syntax error`)
- `perf:` for performance optimizations (e.g., `perf: optimize vector loops in indicator checks`)
- `style:` for style, formatting, or lint-only fixes (e.g., `style: run ruff formatter on doctor`)

---

## 🎯 Your Mission: Enhance System Diagnostics

As an institutional-grade system, our "Time to First Success" is critical. Your mission is to improve the `scripts/doctor.py` tool by adding a new diagnostic check or improving an existing one. This is a high-impact, low-risk way to help every developer who joins after you.

### Step 1: Prepare Your Environment

Make sure you have run the bootstrap command to initialize your python virtual environment:

```bash
# 1. Update your local main
git checkout main
git pull origin main

# 2. Create a feature branch with a valid prefix
git checkout -b feature/doctor-enhancement
```

### Step 2: Identify a Diagnostic Gap

Run the doctor script using the local virtual environment and look for missing checks that would be helpful for a new user:
```bash
./venv/bin/python3 scripts/doctor.py
```

**Ideas for first contributions:**
- Add a check for the existence of the `data/` and `logs/` directories.
- Improve the error message for a failing database connectivity check.
- Add a check to verify that `docker` is installed if the user is in a Linux environment.
- Add a check for specific OS-level dependencies (like `libta-lib0`).

---

## 🛠️ Step-by-Step Walkthrough: Adding a Directory Check

Let's walk through how to add a check for the existence of critical workspace directories (`data/` and `logs/`).

### 1. Implement the Check in `scripts/doctor.py`

Open `scripts/doctor.py` and locate the `DiagnosticCheck` class. Implement a new check function:

```python
def check_workspace_directories():
    """Verify that required data and logs directories exist."""
    required_dirs = ["data", "logs"]
    missing = []

    for d in required_dirs:
        p = Path(d)
        if not p.exists():
            missing.append(d)

    if missing:
        remedy = f"Required directories missing. The system auto-creates them on boot, or you can run: mkdir {' '.join(missing)}"
        return DiagnosticCheck(
            "Workspace Directories",
            "WARNING",
            f"Missing: {', '.join(missing)}",
            remedy
        )
    else:
        return DiagnosticCheck(
            "Workspace Directories",
            "OK",
            "Required data/ and logs/ directories exist"
        )
```

Add your new check function to the `system_checks` list in `main()` of `scripts/doctor.py`:

```python
    system_checks = [
        check_python_version(),
        check_venv(),
        check_workspace_directories(),  # <-- Your new check!
        check_disk_space(),
        ...
    ]
```

### 2. Write the Corresponding Unit Test in `tests/test_doctor_diagnostics.py`

Every diagnostic check added to `scripts/doctor.py` **must** have a corresponding unit test to maintain our strict statement coverage threshold.

Open `tests/test_doctor_diagnostics.py` and add:

```python
def test_check_workspace_directories_missing():
    """Verify that workspace check warns when directories are missing."""
    def mock_exists_side_effect(path):
        # Pretend "data" and "logs" do not exist
        if str(path) in ["data", "logs"]:
            return False
        return True

    with patch("scripts.doctor.Path.exists", side_effect=mock_exists_side_effect):
        res = doctor.check_workspace_directories()
        assert res.status == "WARNING"
        assert "Missing: data, logs" in res.message


def test_check_workspace_directories_ok():
    """Verify that workspace check passes when directories exist."""
    with patch("scripts.doctor.Path.exists", return_value=True):
        res = doctor.check_workspace_directories()
        assert res.status == "OK"
```

### 3. Run and Verify Your Unit Tests Locally

We enforce clean test outcomes before any code is reviewed. Always run the tests inside the virtual environment:

```bash
# Run only doctor diagnostic unit tests
./venv/bin/python3 -m pytest tests/test_doctor_diagnostics.py

# Verify the complete system health via system doctor
./venv/bin/python3 scripts/doctor.py
```

Ensure all tests pass and your new check is outputted cleanly!

---

## 🛡️ Quality Gate & Submission Checklist

Before submitting your PR:

1.  **Branch Prefix:** Ensure your branch has a valid prefix (`feature/`, `bugfix/`, `hotfix/`, `docs/`, `refactor/`, `chore/`, `test/`, `ci/`, `perf/`, `style/`).
2.  **Conventional Commits:** Commit your change with an approved semantic type (e.g., `chore: add workspace directory checks to doctor`).
3.  **Run Governance Suite:** Run the project's governance validator to ensure all files match expectations:
    ```bash
    ./venv/bin/python3 -m pytest tests/test_governance_vitals.py --noconftest
    ```
4.  **Resync with Main (Critical):** Always rebase just before pushing to ensure you are on the latest commit on main:
    ```bash
    make resync
    ```
5.  **Tag for Review:** Open a PR with an approved semantic title (e.g., `docs: improve developer onboarding experience`) and tag **Jules06 (@qufuwan)** for review.

---

## 🆘 Need Help?

If you get stuck on a dependency conflict or setup issue:
1.  Check [docs/status/PROJECT_HEALTH.md](./status/PROJECT_HEALTH.md).
2.  Open a Discussion on GitHub.
3.  Tag a maintainer in your Draft PR.

Thank you for helping us make this system more enterprise-grade!

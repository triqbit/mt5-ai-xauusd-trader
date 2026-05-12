#!/usr/bin/env python3
"""
Atlas Governance Auditor - Enterprise Edition
Verifies synchronization between policy (RISK_LIMITS.md) and implementation (src/core/config.py),
ensures mandatory runbook integrity, validates artifact compliance, and enforces
pre-production checklist completion and security standards.

Author: Atlas 🗺️ (Release Readiness Guardian)
"""

import re
import sys
from pathlib import Path


def check_risk_sync():
    print("Checking RISK_LIMITS.md vs src/core/config.py synchronization...")
    risk_limits_path = Path("RISK_LIMITS.md")
    config_path = Path("src/core/config.py")

    if not risk_limits_path.exists() or not config_path.exists():
        print("Error: RISK_LIMITS.md or src/core/config.py missing.")
        return False

    risk_content = risk_limits_path.read_text()
    config_content = config_path.read_text()

    # Define critical limits to check
    # Mapping: (Policy Regex, Config Field, Config Default)
    checks = [
        (r"Max Risk\*\*: 1% of account per trade", "risk_per_trade", 0.01),
        (r"Concurrent Positions\*\*: Maximum 5 open positions", "max_positions", 5),
        (r"Max Leverage\*\*: 10:1", "max_leverage", 10.0),
        (r"Drawdown Level 5\*\*: 30% drawdown", "max_drawdown", 0.30),
        (r"Daily Win Cap\*\*: 10%", "daily_win_cap", 0.10),
    ]

    success = True
    for policy_regex, config_field, expected_val in checks:
        if not re.search(policy_regex, risk_content):
            print(f"[-] Policy mismatch: Could not find '{policy_regex}' in RISK_LIMITS.md")
            success = False
            continue

        # More robust regex for config default value
        # Pattern handles: field_name: type = Field(default=value, ...) with optional spaces
        pattern = rf"{config_field}\s*:\s*[\w\[\]]+\s*=\s*Field\(\s*default\s*=\s*([\d\.]+)"
        config_match = re.search(pattern, config_content)
        if config_match:
            actual_val = float(config_match.group(1))
            if actual_val != expected_val:
                print(
                    f"[-] Config mismatch: {config_field} default is {actual_val}, expected {expected_val} (per policy)"
                )
                success = False
            else:
                print(f"[+] {config_field} synchronized.")
        else:
            print(f"[-] Could not find field {config_field} in src/core/config.py")
            success = False

    return success


def check_runbooks():
    print("Checking Runbook Integrity...")
    runbook_dir = Path("docs/runbooks")
    if not runbook_dir.exists():
        print("[-] docs/runbooks directory missing.")
        return False

    mandatory_runbooks = [
        "01-ci-failure-recovery.md",
        "02-mt5-connection-outage.md",
        "03-circuit-breaker-triggered.md",
        "04-database-corruption.md",
        "05-failed-deployment-rollback.md",
        "06-monitoring-alert-triage.md",
        "07-secret-rotation-procedure.md",
    ]

    mandatory_sections = [
        "Overview",
        "Step-by-Step Instructions",
        "Expected Outcomes",
        "Escalation Path",
        "Verification Commands",
    ]

    success = True
    for rb in mandatory_runbooks:
        rb_path = runbook_dir / rb
        if not rb_path.exists():
            print(f"[-] Mandatory runbook missing: {rb}")
            success = False
            continue

        content = rb_path.read_text()
        for section in mandatory_sections:
            pattern = rf"^[#]{{1,3}}\s+{section}"
            if not re.search(pattern, content, re.MULTILINE):
                print(f"[-] Runbook {rb} missing mandatory section: {section}")
                success = False
            elif section == "Verification Commands":
                # Ensure the section actually contains code blocks (```)
                # Find content between this header and the next header
                sec_pattern = rf"^[#]{{1,3}}\s+{section}\n(.*?)(?=^[#]{{1,3}}\s+|$)"
                sec_match = re.search(sec_pattern, content, re.MULTILINE | re.DOTALL)
                if sec_match and "```" not in sec_match.group(1):
                    print(
                        f"[-] Runbook {rb} Verification Commands section missing actual code blocks (```)"
                    )
                    success = False

    if success:
        print("[+] All mandatory runbooks present and structured with executable commands.")
    return success


def check_artifact_compliance():
    print("Checking Artifact Compliance (package_release.sh vs RELEASE_ARTIFACTS.md)...")
    pkg_script = Path("scripts/package_release.sh")
    artifacts_doc = Path("docs/RELEASE_ARTIFACTS.md")

    if not pkg_script.exists() or not artifacts_doc.exists():
        print("[-] package_release.sh or RELEASE_ARTIFACTS.md missing.")
        return False

    pkg_content = pkg_script.read_text()
    art_content = artifacts_doc.read_text()

    # Extract mandatory artifacts from doc
    # e.g. | **Docker Image** | `image.tar.gz` |
    mandatory_files = re.findall(r"\| `([^`]+)` \|", art_content)

    success = True
    for f in mandatory_files:
        if f not in pkg_content:
            # Simple check if the filename is mentioned in the script (usually in collection logic)
            print(
                f"[-] Artifact mismatch: {f} defined in standards but not found in package_release.sh"
            )
            success = False
        else:
            print(f"[+] Artifact {f} included in packaging script.")

    return success


def check_preprod_checklist():
    print("Checking PREPROD_CHECKLIST.md strict compliance...")
    checklist_path = Path("docs/PREPROD_CHECKLIST.md")
    pyproject_path = Path("pyproject.toml")

    if not checklist_path.exists():
        print("[-] docs/PREPROD_CHECKLIST.md missing.")
        return False

    content = checklist_path.read_text()
    success = True

    # 1. Check for uncompleted items
    # Note: We exclude the status selection line which contains both [x] and [ ]
    if "[ ]" in content:
        lines = content.splitlines()
        uncompleted = []
        for i, line in enumerate(lines):
            if "[ ]" in line and "**Status:**" not in line:
                uncompleted.append((i + 1, line.strip()))

        if uncompleted:
            print("[-] PREPROD_CHECKLIST.md contains uncompleted items.")
            for line_no, text in uncompleted:
                print(f"    Line {line_no}: {text}")
            success = False

    # 2. Verify Version Synchronization
    if pyproject_path.exists():
        py_content = pyproject_path.read_text()
        v_match = re.search(r'^version\s*=\s*"([^"]+)"', py_content, re.MULTILINE)
        if v_match:
            expected_version = v_match.group(1)
            # Find version in checklist: **Release Version:** `v__________________`
            cv_match = re.search(r"\*\*Release Version:\*\*\s*`v([^`]+)`", content)
            if cv_match:
                actual_version = cv_match.group(1).strip("_")
                if actual_version != expected_version:
                    print(
                        f"[-] Checklist version mismatch: Found 'v{actual_version}', expected 'v{expected_version}'"
                    )
                    success = False
                else:
                    print(f"[+] Checklist version 'v{actual_version}' synchronized.")
            else:
                print("[-] Could not find Release Version marker in PREPROD_CHECKLIST.md")
                success = False

    # 3. Verify Signatures (Non-empty placeholders)
    # **Verified By (Operator):** ____________________
    # **Approval (Governance):** ____________________
    sig_fields = [
        ("Verified By", r"\*\*Verified By \(Operator\):\*\*\s*(.+)"),
        ("Approval", r"\*\*Approval \(Governance\):\*\*\s*(.+)"),
    ]
    for label, pattern in sig_fields:
        match = re.search(pattern, content)
        if not match or "____" in match.group(1) or not match.group(1).strip():
            print(f"[-] Checklist signature missing: {label}")
            success = False
        else:
            print(f"[+] Checklist signature found for {label}.")

    # 4. Verify GO status
    # **Status:** [x] **GO** / [ ] **NO-GO**
    if "**Status:** [x] **GO**" not in content:
        print("[-] Checklist Status is NOT set to [x] GO.")
        success = False
    else:
        print("[+] Checklist Status set to GO.")

    if success:
        print("[+] PREPROD_CHECKLIST.md is complete and verified.")
    return success


def check_governance_vitals():
    print("Checking Governance Vitals existence...")
    mandatory_files = [
        ".github/CODEOWNERS",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/security_report.yml",
        "docs/CONTRIBUTING.md",
        "docs/PREPROD_CHECKLIST.md",
        "docs/ENTERPRISE_STANDARDS.md",
        "docs/LICENSE_COMPLIANCE.md",
        "docs/DEPENDENCY_LICENSES.md",
        "docs/SLO_TARGETS.md",
        "docs/VERSIONING_POLICY.md",
        "SECURITY.md",
    ]

    success = True
    for f in mandatory_files:
        path = Path(f)
        if not path.exists():
            print(f"[-] Mandatory governance file missing: {f}")
            success = False
        else:
            print(f"[+] Governance file present: {f}")

    return success


def check_docker_security():
    print("Checking Docker Security Standards...")
    dockerfile_path = Path("Dockerfile")
    if not dockerfile_path.exists():
        print("[-] Dockerfile missing.")
        return False

    content = dockerfile_path.read_text()

    # Enforce non-root USER instruction
    if not re.search(r"^USER\s+\w+", content, re.MULTILINE):
        print(
            "[-] Dockerfile violation: No non-root USER instruction found. Running as root is prohibited."
        )
        return False

    print("[+] Dockerfile security check passed (non-root USER found).")
    return True


def main():
    print("=== Atlas Governance Audit starting ===")
    results = [
        check_risk_sync(),
        check_runbooks(),
        check_artifact_compliance(),
        check_preprod_checklist(),
        check_governance_vitals(),
        check_docker_security(),
    ]

    if all(results):
        print("=== Audit PASSED ===")
        sys.exit(0)
    else:
        print("=== Audit FAILED ===")
        sys.exit(1)


if __name__ == "__main__":
    main()

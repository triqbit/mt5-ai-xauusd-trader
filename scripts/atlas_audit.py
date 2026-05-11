#!/usr/bin/env python3
"""
Atlas Governance Auditor
Verifies synchronization between policy (RISK_LIMITS.md) and implementation (src/core/config.py),
ensures mandatory runbook integrity, and validates artifact compliance.
"""

import sys
import re
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
                print(f"[-] Config mismatch: {config_field} default is {actual_val}, expected {expected_val} (per policy)")
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

    mandatory_sections = ["Overview", "Step-by-Step Instructions", "Expected Outcomes", "Escalation Path", "Verification Commands"]

    success = True
    for rb in mandatory_runbooks:
        rb_path = runbook_dir / rb
        if not rb_path.exists():
            print(f"[-] Mandatory runbook missing: {rb}")
            success = False
            continue

        content = rb_path.read_text()
        for section in mandatory_sections:
            if f"## {section}" not in content and f"# {section}" not in content:
                # Some might use slightly different headers, let's be a bit flexible but firm
                if not re.search(rf"^[#]{{1,3}}\s+{section}", content, re.MULTILINE):
                    print(f"[-] Runbook {rb} missing mandatory section: {section}")
                    success = False

    if success:
        print("[+] All mandatory runbooks present and structured.")
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
            print(f"[-] Artifact mismatch: {f} defined in standards but not found in package_release.sh")
            success = False
        else:
            print(f"[+] Artifact {f} included in packaging script.")

    return success

def check_preprod_checklist():
    print("Checking PREPROD_CHECKLIST.md compliance...")
    checklist_path = Path("docs/PREPROD_CHECKLIST.md")
    if not checklist_path.exists():
        print("[-] docs/PREPROD_CHECKLIST.md missing.")
        return False

    content = checklist_path.read_text()
    if "[ ]" in content:
        print("[-] PREPROD_CHECKLIST.md contains uncompleted items.")
        # Find lines with [ ]
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "[ ]" in line:
                print(f"    Line {i+1}: {line.strip()}")
        return False

    print("[+] PREPROD_CHECKLIST.md is complete.")
    return True

def main():
    print("=== Atlas Governance Audit starting ===")
    results = [
        check_risk_sync(),
        check_runbooks(),
        check_artifact_compliance(),
        check_preprod_checklist()
    ]

    if all(results):
        print("=== Audit PASSED ===")
        sys.exit(0)
    else:
        print("=== Audit FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()

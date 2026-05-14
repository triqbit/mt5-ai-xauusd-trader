#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Version Synchronization Guard
scripts/verify_version_sync.py

Ensures version consistency across:
- pyproject.toml
- src/__init__.py
- CHANGELOG.md (Latest released version)
"""

import re
import sys
from pathlib import Path


def extract_version_pyproject(root: Path) -> str:
    path = root / "pyproject.toml"
    if not path.exists():
        return "MISSING"
    content = path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else "NOT_FOUND"


def extract_version_init(root: Path) -> str:
    path = root / "src" / "__init__.py"
    if not path.exists():
        return "MISSING"
    content = path.read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else "NOT_FOUND"


def extract_version_changelog(root: Path) -> str:
    path = root / "CHANGELOG.md"
    if not path.exists():
        return "OPTIONAL_MISSING"
    content = path.read_text()
    # Find the first header like ## [X.Y.Z] that is NOT [Unreleased]
    # We look for ## [ followed by something that isn't Unreleased
    matches = re.finditer(r"## \[([^\]]+)\]", content)
    for match in matches:
        version = match.group(1)
        if version.lower() != "unreleased":
            return version

    return "NOT_FOUND"


def main():
    root = Path(__file__).resolve().parents[1]

    pyproject_v = extract_version_pyproject(root)
    init_v = extract_version_init(root)
    changelog_v = extract_version_changelog(root)

    print("--- Version Sync Audit ---")
    print(f"pyproject.toml:  {pyproject_v}")
    print(f"src/__init__.py: {init_v}")
    print(f"CHANGELOG.md:    {changelog_v}")
    print("-" * 26)

    # Authoritative set
    authoritative = {
        "pyproject.toml": pyproject_v,
        "src/__init__.py": init_v,
    }

    errors = []
    for file, version in authoritative.items():
        if version in ("MISSING", "NOT_FOUND"):
            errors.append(f"CRITICAL: Version marker in {file} is {version}")

    if errors:
        for err in errors:
            print(err)
        sys.exit(1)

    # If CHANGELOG exists, it must also match
    if changelog_v not in ("OPTIONAL_MISSING", "NOT_FOUND"):
        authoritative["CHANGELOG.md"] = changelog_v
    elif changelog_v == "NOT_FOUND":
        print("=" * 60)
        print("❌ DEPLOYMENT BLOCKED: CHANGELOG.md VERSION MISSING")
        print("=" * 60)
        print("Error: No versioned headers found in CHANGELOG.md (only [Unreleased]?)")
        print("REMEDIATION: Add a versioned header matching the release (e.g. ## [1.2.3]).")
        print("=" * 60)
        sys.exit(1)

    unique_versions = set(authoritative.values())

    if len(unique_versions) > 1:
        print("=" * 60)
        print("❌ DEPLOYMENT BLOCKED: VERSION MISMATCH DETECTED")
        print("=" * 60)
        for file, version in authoritative.items():
            print(f"  - {file}: {version}")
        print("\nREMEDIATION: Ensure all shared version markers share the same semantic version.")
        print("Update pyproject.toml and src/__init__.py to match the target release.")
        print("=" * 60)
        sys.exit(1)

    print("✅ SUCCESS: All version markers are synchronized.")
    sys.exit(0)


if __name__ == "__main__":
    main()

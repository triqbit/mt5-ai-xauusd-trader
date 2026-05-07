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
    match = re.search(r'## \[([^\]]+)\]', content)
    if match:
        if match.group(1).lower() == "unreleased":
            # Search for the next one
            match = re.search(r'## \[([^\]]+)\]', content[match.end():])

    return match.group(1) if match else "NOT_FOUND"

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

    # If CHANGELOG exists, it must also match
    if changelog_v != "OPTIONAL_MISSING":
        authoritative["CHANGELOG.md"] = changelog_v

    # Filter out missing/not found
    valid_versions = {k: v for k, v in authoritative.items() if v not in ("MISSING", "NOT_FOUND")}

    if len(valid_versions) < len(authoritative):
        print("ERROR: One or more authoritative version files are missing or malformed.")
        sys.exit(1)

    unique_versions = set(valid_versions.values())

    if len(unique_versions) > 1:
        print("❌ DEPLOYMENT BLOCKED: Version mismatch detected!")
        print("Remediation: Ensure all shared version markers share the same semantic version.")
        sys.exit(1)

    print("✅ SUCCESS: All version markers are synchronized.")
    sys.exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MT5 AI/ML Trading Bot - Version Bumping Tool
scripts/bump_version.py

Automates version updates in:
- pyproject.toml
- src/__init__.py
- CHANGELOG.md (Transitions [Unreleased] to versioned header)
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def bump_pyproject(root: Path, version: str, dry_run: bool = False):
    path = root / "pyproject.toml"
    if not path.exists():
        print(f"Error: {path} not found")
        return False

    content = path.read_text()
    new_content = re.sub(
        r'(^version\s*=\s*")([^"]+)(")', rf"\g<1>{version}\g<3>", content, flags=re.MULTILINE
    )

    if content == new_content:
        print(f"Warning: Version in {path} is already {version} or could not be updated.")
    else:
        print(f"Updating {path} to {version}")
        if not dry_run:
            path.write_text(new_content)
    return True


def bump_init(root: Path, version: str, dry_run: bool = False):
    path = root / "src" / "__init__.py"
    if not path.exists():
        print(f"Warning: {path} not found, skipping.")
        return True

    content = path.read_text()
    new_content = re.sub(
        r'(^__version__\s*=\s*")([^"]+)(")', rf"\g<1>{version}\g<3>", content, flags=re.MULTILINE
    )

    if content == new_content:
        print(f"Warning: Version in {path} is already {version} or could not be updated.")
    else:
        print(f"Updating {path} to {version}")
        if not dry_run:
            path.write_text(new_content)
    return True


def bump_changelog(root: Path, version: str, dry_run: bool = False):
    path = root / "CHANGELOG.md"
    if not path.exists():
        print(f"Warning: {path} not found, skipping.")
        return True

    content = path.read_text()
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Transition [Unreleased] to [Version] - Date
    unreleased_pattern = r"## \[Unreleased\]"
    new_header = f"## [Unreleased]\n\n## [{version}] - {date_str}"

    if re.search(unreleased_pattern, content):
        print(f"Updating {path}: Transitioning [Unreleased] to [{version}]")
        new_content = re.sub(unreleased_pattern, new_header, content)
        if not dry_run:
            path.write_text(new_content)
    else:
        print(f"Warning: [Unreleased] section not found in {path}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Bump project version.")
    parser.add_argument("version", help="New semantic version (e.g., 1.2.3)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes to disk")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    version = args.version

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+(-[a-z0-9.]+)?$", version):
        print(
            f"Error: Invalid version format '{version}'. Must be SemVer (e.g., 1.2.3 or 1.2.3-rc.1)"
        )
        sys.exit(1)

    success = True
    success &= bump_pyproject(root, version, args.dry_run)
    success &= bump_init(root, version, args.dry_run)
    success &= bump_changelog(root, version, args.dry_run)

    if success:
        print(f"\nSuccessfully bumped to version {version}")
    else:
        print("\nFailed to bump version.")
        sys.exit(1)


if __name__ == "__main__":
    main()

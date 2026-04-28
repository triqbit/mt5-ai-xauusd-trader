import sys
import os
from pathlib import Path

def validate_release_notes():
    repo_root = Path(__file__).resolve().parents[1]
    changelog_path = repo_root / "CHANGELOG.md"

    if not changelog_path.exists():
        print(f"Error: {changelog_path} does not exist.")
        return False

    with open(changelog_path, "r") as f:
        content = f.read().strip()

    if not content:
        print("Error: CHANGELOG.md is empty.")
        return False

    # Check if it has more than just a title (placeholder check)
    lines = [line for line in content.split("\n") if line.strip()]
    if len(lines) < 2:
         print("Error: CHANGELOG.md contains no meaningful release notes.")
         return False

    print("CHANGELOG.md is valid and non-empty.")
    return True

if __name__ == "__main__":
    if not validate_release_notes():
        sys.exit(1)
    sys.exit(0)

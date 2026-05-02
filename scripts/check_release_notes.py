import sys
import re
from pathlib import Path


def check_release_notes():
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("Error: CHANGELOG.md not found.")
        return False

    with open(changelog_path, "r") as f:
        content = f.read()

    # Find the [Unreleased] section
    # It starts with ## [Unreleased] and ends at the next ## header or end of file
    pattern = r"## \[Unreleased\](.*?)(?=\n## |$)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("Error: [Unreleased] section not found in CHANGELOG.md")
        return False

    unreleased_content = match.group(1).strip()

    # Check if there is any actual content (ignoring empty subheaders)
    # We look for lines starting with '-' or containing actual text
    lines = unreleased_content.splitlines()
    has_content = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("###") and not stripped.startswith("##"):
            # If it's not a header and not empty, it's likely content
            if any(c.isalnum() for c in stripped):
                has_content = True
                break

    if not has_content:
        print("Error: [Unreleased] section in CHANGELOG.md is empty.")
        print("Please add release notes before deploying.")
        return False

    print("Success: [Unreleased] section has content.")
    return True


if __name__ == "__main__":
    if not check_release_notes():
        sys.exit(1)
    sys.exit(0)

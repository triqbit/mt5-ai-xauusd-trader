import re
import sys
from pathlib import Path


def check_release_notes():
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("=" * 60)
        print("  DEPLOYMENT BLOCKED: CHANGELOG.md MISSING")
        print("=" * 60)
        print("Error: CHANGELOG.md not found in repository root.")
        return False

    with open(changelog_path, "r") as f:
        content = f.read()

    # Find the [Unreleased] section
    # It starts with ## [Unreleased] and ends at the next ## header or end of file
    pattern = r"## \[Unreleased\](.*?)(?=\n## |$)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("=" * 60)
        print("  DEPLOYMENT BLOCKED: [Unreleased] SECTION MISSING")
        print("=" * 60)
        print("Error: [Unreleased] section not found in CHANGELOG.md")
        print("REMEDIATION: Add a '## [Unreleased]' header to CHANGELOG.md.")
        return False

    unreleased_content = match.group(1).strip()

    # Check if there is any actual content (ignoring empty subheaders)
    # We look for lines starting with '-' or containing actual text
    lines = unreleased_content.splitlines()
    has_content = False
    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("###")
            and not stripped.startswith("##")
            and any(c.isalnum() for c in stripped)
        ):
            # If it's not a header and not empty and has alnum, it's likely content
            has_content = True
            break

    if not has_content:
        print("=" * 60)
        print("  DEPLOYMENT BLOCKED: RELEASE NOTES EMPTY")
        print("=" * 60)
        print("Error: [Unreleased] section in CHANGELOG.md exists but has no descriptive content.")
        print("REMEDIATION: Add details about your changes under the [Unreleased] section.")
        print("Follow Conventional Commits format (e.g., - feat: describe feature).")
        print("=" * 60)
        return False

    print("SUCCESS: [Unreleased] section has content. Release notes validation passed.")
    return True


if __name__ == "__main__":
    if not check_release_notes():
        sys.exit(1)
    sys.exit(0)

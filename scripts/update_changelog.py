import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd_args):
    """Run a command safely without shell=True."""
    try:
        result = subprocess.run(cmd_args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since_last_tag():
    last_tag = run_command(["git", "describe", "--tags", "--abbrev=0"])
    if not last_tag:
        # Fallback to all commits if no tag exists
        cmd = ["git", "log", "--pretty=format:%B%n-DELIMITER-"]
    else:
        cmd = ["git", "log", f"{last_tag}..HEAD", "--pretty=format:%B%n-DELIMITER-"]

    output = run_command(cmd)
    if not output:
        return []

    # Split by delimiter and filter empty entries
    commits = [c.strip() for c in output.split("-DELIMITER-") if c.strip()]
    return commits


def categorize_commits(commits, labels=None):
    categories = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Security": [],
        "Deprecated": [],
        "Removed": [],
    }

    mapping = {
        "feat": "Added",
        "fix": "Fixed",
        "security": "Security",
        "perf": "Changed",
        "refactor": "Changed",
        "docs": "Changed",
        "style": "Changed",
        "chore": "Changed",
        "ci": "Changed",
        "test": "Changed",
        "revert": "Changed",
        "deprecate": "Deprecated",
        "remove": "Removed",
    }

    # If PR labels are provided, they influence categorization
    label_to_cat = {}
    if labels:
        label_mapping = {
            "enhancement": "Added",
            "feature": "Added",
            "bug": "Fixed",
            "fix": "Fixed",
            "security": "Security",
            "documentation": "Changed",
            "refactor": "Changed",
            "deprecated": "Deprecated",
            "removal": "Removed",
            "release:major": "Changed",
            "release:minor": "Changed",
            "release:patch": "Fixed",
        }
        for label in labels:
            cat = label_mapping.get(label.lower())
            if cat:
                label_to_cat[label.lower()] = cat

    for commit in commits:
        # Split into lines to separate subject from body
        lines = commit.splitlines()
        if not lines:
            continue

        subject = lines[0]
        # Filter out metadata lines from body (Co-authored-by, etc.)
        body_lines = [
            line
            for line in lines[1:]
            if not any(
                marker in line
                for marker in ["Co-authored-by:", "Signed-off-by:", "PR-URL:", "---------"]
            )
        ]
        body = "\n".join(body_lines).strip()

        # Ignore automated changelog updates and release commits
        if "docs: update CHANGELOG.md" in subject or "chore: release v" in subject:
            continue

        # Try to parse conventional commit from subject
        # Pattern: ^(\w+)(?:\(([^)]+)\))?(!?): (.+)$
        match = re.match(r"^(\w+)(?:\(([^)]+)\))?(!?): (.+)$", subject)
        if match:
            ctype, scope, breaking, message = match.groups()
            category = mapping.get(ctype, "Changed")

            # Capitalize first letter of message
            message = message[0].upper() + message[1:]

            is_breaking = (
                breaking == "!" or "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body
            )

            entry = f"- {message}"
            if scope:
                entry = f"- **{scope}**: {message}"

            if is_breaking:
                entry = f"- **BREAKING CHANGE**: {message}"
                if scope:
                    entry = f"- **BREAKING CHANGE** ({scope}): {message}"

            if entry not in categories[category]:
                categories[category].append(entry)
        else:
            # Non-conventional commit
            if subject.strip() and not subject.startswith("Merge "):
                message = subject.strip()
                message = message[0].upper() + message[1:]

                is_breaking = "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body
                entry = f"- {message}"
                if is_breaking:
                    entry = f"- **BREAKING CHANGE**: {message}"

                # Determine category: labels > default (Changed)
                category = "Changed"
                if label_to_cat:
                    # Use the first matching label as category
                    category = next(iter(label_to_cat.values()))

                if entry not in categories[category]:
                    categories[category].append(entry)

    return {k: v for k, v in categories.items() if v}


def update_changelog(categories):
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("CHANGELOG.md not found")
        return False

    content = changelog_path.read_text()

    # Split by ## [Unreleased]
    parts = re.split(r"(## \[Unreleased\])", content)
    if len(parts) < 3:
        print("[Unreleased] section not found in CHANGELOG.md")
        return False

    prefix = parts[0]
    unreleased_header = parts[1]
    remainder = parts[2]

    # Split remainder to separate Unreleased content from the rest of the changelog
    # It ends at the next ## header
    sub_parts = re.split(r"(\n## \[)", remainder, maxsplit=1)
    unreleased_content = sub_parts[0]
    rest_of_changelog = sub_parts[1] + sub_parts[2] if len(sub_parts) > 1 else ""

    # Ensure categories are processed in a specific order
    order = ["Added", "Changed", "Fixed", "Security", "Deprecated", "Removed"]
    sorted_categories = [(cat, categories[cat]) for cat in order if cat in categories]
    # Add any other categories that might be there
    for cat, entries in categories.items():
        if cat not in order:
            sorted_categories.append((cat, entries))

    for category, entries in sorted_categories:
        header = f"### {category}"
        if header not in unreleased_content:
            # If category doesn't exist, append to the end of the unreleased section
            unreleased_content = (
                unreleased_content.rstrip() + f"\n\n{header}\n" + "\n".join(entries) + "\n"
            )
        else:
            # If category exists, append only new entries
            lines = unreleased_content.splitlines()
            category_index = -1
            for i, line in enumerate(lines):
                if line.strip() == header:
                    category_index = i
                    break

            if category_index != -1:
                # Find where this category ends
                end_index = len(lines)
                for i in range(category_index + 1, len(lines)):
                    if lines[i].startswith("### ") or lines[i].startswith("## "):
                        end_index = i
                        break

                # Backtrack to avoid inserting before empty lines
                while end_index > category_index + 1 and not lines[end_index - 1].strip():
                    end_index -= 1

                existing_entries = [
                    line.strip()
                    for line in lines[category_index + 1 : end_index]
                    if line.strip().startswith("- ")
                ]
                for entry in entries:
                    if entry not in existing_entries:
                        lines.insert(end_index, entry)
                        end_index += 1

                unreleased_content = "\n".join(lines)

    new_content = (
        prefix
        + unreleased_header
        + unreleased_content.rstrip()
        + "\n\n"
        + rest_of_changelog.lstrip()
    )
    changelog_path.write_text(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md from commits and labels.")
    parser.add_argument("--labels", nargs="*", help="PR labels to assist categorization.")
    args = parser.parse_args()

    # If labels is a single string with spaces, split it
    labels = args.labels
    if labels and len(labels) == 1 and " " in labels[0]:
        labels = labels[0].split()

    commits = get_commits_since_last_tag()
    if not commits:
        print("No new commits found.")
        return

    categories = categorize_commits(commits, labels=labels)
    if not categories:
        print("No relevant commits found.")
        return

    if update_changelog(categories):
        print("CHANGELOG.md updated successfully.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

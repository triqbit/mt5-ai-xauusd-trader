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
        cmd = ["git", "log", "--pretty=format:%s"]
    else:
        cmd = ["git", "log", f"{last_tag}..HEAD", "--pretty=format:%s"]

    output = run_command(cmd)
    if not output:
        return []
    return output.splitlines()


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
        "perf": "Added",
        "refactor": "Changed",
        "docs": "Changed",
        "style": "Changed",
        "chore": "Changed",
        "ci": "Changed",
        "test": "Changed",
    }

    # If PR labels are provided, they can influence the categorization of the LAST commit
    # (assuming the script runs on a push that is likely a PR merge)
    if labels:
        label_categories = {
            "release:major": "Added", # Usually involves new features/major changes
            "release:minor": "Added",
            "release:patch": "Fixed",
        }
        # Standard GitHub labels mapping
        label_categories.update({
            "enhancement": "Added",
            "bug": "Fixed",
            "security": "Security",
            "documentation": "Changed",
        })

        for label in labels:
            cat = label_categories.get(label.lower())
            if cat and commits:
                # Use the PR title (first commit in a squash merge) or just add a generic entry if needed
                # For now, we'll still rely on commit messages but use labels as fallback or boost
                pass

    for commit in commits:
        # Ignore automated changelog updates and release commits
        if "docs: update CHANGELOG.md" in commit or "chore: release v" in commit:
            continue

        # Try to parse conventional commit
        match = re.match(r"^(\w+)(?:\(.+\))?(!?): (.+)$", commit)
        if match:
            ctype, breaking, message = match.groups()
            category = mapping.get(ctype, "Changed")

            # Capitalize first letter of message
            message = message[0].upper() + message[1:]

            entry = f"- {message}"
            if breaking == "!":
                entry = f"- **BREAKING CHANGE**: {message}"

            if entry not in categories[category]:
                categories[category].append(entry)
        else:
            # Non-conventional commit - put in Changed by default if it's not empty
            if commit.strip() and not commit.startswith("Merge "):
                message = commit.strip()
                message = message[0].upper() + message[1:]
                entry = f"- {message}"
                if entry not in categories["Changed"]:
                    categories["Changed"].append(entry)

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

    # Merge new categories into unreleased_content
    for category, entries in categories.items():
        header = f"### {category}"
        if header not in unreleased_content:
            # If category doesn't exist, append it
            unreleased_content = unreleased_content.strip() + f"\n\n{header}\n" + "\n".join(entries) + "\n"
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

                existing_entries = [line.strip() for line in lines[category_index+1:end_index] if line.strip().startswith("- ")]
                for entry in entries:
                    if entry not in existing_entries:
                        lines.insert(end_index, entry)
                        end_index += 1

                unreleased_content = "\n".join(lines)

    new_content = prefix + unreleased_header + unreleased_content.rstrip() + "\n\n" + rest_of_changelog.lstrip()
    changelog_path.write_text(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(description="Update CHANGELOG.md from commits and labels.")
    parser.add_argument("--labels", nargs="*", help="PR labels to assist categorization.")
    args = parser.parse_args()

    commits = get_commits_since_last_tag()
    if not commits:
        print("No new commits found.")
        return

    categories = categorize_commits(commits, labels=args.labels)
    if not categories:
        print("No relevant commits found.")
        return

    if update_changelog(categories):
        print("CHANGELOG.md updated successfully.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

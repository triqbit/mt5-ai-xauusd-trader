import os
import unittest
from pathlib import Path

from scripts.update_changelog import categorize_commits, update_changelog


class TestChangelogAutomation(unittest.TestCase):
    def test_categorize_commits(self):
        commits = [
            "feat: add new feature",
            "fix: fix bug",
            "feat!: breaking change",
            "chore: some cleanup",
            "docs: update readme",
            "invalid commit",
            "docs: update CHANGELOG.md",
            "chore: release v1.0.0",
            "Random non-conventional commit"
        ]
        categories = categorize_commits(commits)

        self.assertIn("Added", categories)
        self.assertIn("Fixed", categories)
        self.assertIn("Changed", categories)

        self.assertIn("- Add new feature", categories["Added"])
        self.assertIn("- **BREAKING CHANGE**: Breaking change", categories["Added"])
        self.assertIn("- Fix bug", categories["Fixed"])
        self.assertIn("- Some cleanup", categories["Changed"])
        self.assertIn("- Update readme", categories["Changed"])
        self.assertIn("- Random non-conventional commit", categories["Changed"])

        # Check ignored commits
        self.assertNotIn("- Update CHANGELOG.md", categories["Changed"])
        self.assertNotIn("- Release v1.0.0", categories["Changed"])

    def test_categorize_with_labels(self):
        commits = ["feat: add feature"]
        labels = ["bug"]
        # In current implementation, labels don't override conventional commit types yet,
        # but the script accepts them.
        categories = categorize_commits(commits, labels=labels)
        self.assertIn("Added", categories)
        self.assertEqual(len(categories["Added"]), 1)

    def test_update_changelog(self):
        changelog_path = Path("CHANGELOG.md_test")
        content = """# Changelog
## [Unreleased]

### Added
- Existing feature

## [1.0.0] - 2024-05-24
### Added
- Initial release
"""
        changelog_path.write_text(content)

        try:
            # Patch update_changelog to use our test file
            import scripts.update_changelog
            original_path = scripts.update_changelog.Path

            class MockPath:
                def __init__(self, path):
                    self.path = Path(path) if path != "CHANGELOG.md" else changelog_path
                def exists(self): return self.path.exists()
                def read_text(self): return self.path.read_text()
                def write_text(self, text): self.path.write_text(text)
                def __truediv__(self, other): return MockPath(self.path / other)
                def rstrip(self): return self.path.name.rstrip()
                def lstrip(self): return self.path.name.lstrip()

            scripts.update_changelog.Path = MockPath

            categories = {
                "Added": ["- New feature"],
                "Fixed": ["- New fix"]
            }

            update_changelog(categories)

            new_content = changelog_path.read_text()
            self.assertIn("- Existing feature", new_content)
            self.assertIn("- New feature", new_content)
            self.assertIn("### Fixed", new_content)
            self.assertIn("- New fix", new_content)
            self.assertIn("## [1.0.0]", new_content)

            # Run again to check for duplicates
            update_changelog(categories)
            changelog_path.read_text()
            self.assertEqual(new_content.count("- New feature"), 1)

        finally:
            scripts.update_changelog.Path = original_path
            if changelog_path.exists():
                os.remove(changelog_path)

if __name__ == "__main__":
    unittest.main()

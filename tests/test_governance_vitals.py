import unittest
from pathlib import Path


class TestGovernanceVitals(unittest.TestCase):
    """Verify repository governance and vitals integrity."""

    def test_governance_files_exist(self):
        """Verify that mandatory governance files are present in the repository."""
        root = Path(__file__).parent.parent
        mandatory_files = [
            ".github/CODEOWNERS",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/ISSUE_TEMPLATE/security_report.yml",
            "docs/CONTRIBUTING.md",
            "docs/PREPROD_CHECKLIST.md",
            "docs/ENTERPRISE_STANDARDS.md",
            "docs/LICENSE_COMPLIANCE.md",
            "docs/DEPENDENCY_LICENSES.md",
            "docs/SLO_TARGETS.md",
            "SECURITY.md",
        ]

        for file_path in mandatory_files:
            self.assertTrue(
                (root / file_path).exists(),
                f"Mandatory governance file missing: {file_path}",
            )

    def test_codeowners_quality_leads(self):
        """Verify that CODEOWNERS contains lead maintainer handles."""
        root = Path(__file__).parent.parent
        codeowners_path = root / ".github/CODEOWNERS"

        content = codeowners_path.read_text()
        self.assertIn("@andonly1348", content)
        self.assertIn("@maintainer-quality", content)
        self.assertIn("@maintainer-trading", content)
        self.assertIn("@maintainer-models", content)

    def test_contributing_quality_gates(self):
        """Verify that CONTRIBUTING.md defines mandatory quality gates."""
        root = Path(__file__).parent.parent
        contributing_path = root / "docs/CONTRIBUTING.md"

        content = contributing_path.read_text()
        self.assertIn("85%", content)
        self.assertIn("Quality Gates", content)
        self.assertIn("Conventional Commits", content)


if __name__ == "__main__":
    unittest.main()

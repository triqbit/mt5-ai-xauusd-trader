from pathlib import Path


def test_governance_files_exist():
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
        assert (root / file_path).exists(), f"Mandatory governance file missing: {file_path}"

def test_codeowners_quality_leads():
    """Verify that CODEOWNERS contains lead maintainer handles."""
    root = Path(__file__).parent.parent
    codeowners_path = root / ".github/CODEOWNERS"

    content = codeowners_path.read_text()
    assert "@andonly1348" in content
    assert "@maintainer-quality" in content
    assert "@maintainer-trading" in content
    assert "@maintainer-models" in content

def test_contributing_quality_gates():
    """Verify that CONTRIBUTING.md defines mandatory quality gates."""
    root = Path(__file__).parent.parent
    contributing_path = root / "docs/CONTRIBUTING.md"

    content = contributing_path.read_text()
    assert "85%" in content
    assert "Quality Gates" in content
    assert "Conventional Commits" in content

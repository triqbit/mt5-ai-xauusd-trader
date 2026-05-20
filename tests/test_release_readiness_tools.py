
from scripts.verify_version_sync import (
    extract_version_changelog,
    extract_version_init,
    extract_version_pyproject,
)


def test_version_sync_extraction(tmp_path):
    # Setup mock project structure
    (tmp_path / "src").mkdir()

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "1.2.3"\n')

    init_py = tmp_path / "src" / "__init__.py"
    init_py.write_text('__version__ = "1.2.3"\n')

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text('# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-05-07\n')

    assert extract_version_pyproject(tmp_path) == "1.2.3"
    assert extract_version_init(tmp_path) == "1.2.3"
    assert extract_version_changelog(tmp_path) == "1.2.3"

def test_version_sync_changelog_robustness(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"

    # Case 1: No Unreleased section
    changelog.write_text('## [1.1.0] - 2026-01-01\n')
    assert extract_version_changelog(tmp_path) == "1.1.0"

    # Case 2: Missing CHANGELOG
    changelog.unlink()
    assert extract_version_changelog(tmp_path) == "OPTIONAL_MISSING"

def test_smoke_test_logic(monkeypatch):
    from scripts.smoke_test import check_api_health

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json

    def mock_get(url, timeout=None):
        if "liveness" in url:
            return MockResponse(200, {"status": "ok"})
        if "readiness" in url:
            return MockResponse(200, {"version": "1.1.0", "components": {}})
        return MockResponse(404, {})

    import httpx
    monkeypatch.setattr(httpx, "get", mock_get)

    results = check_api_health("http://mock")
    assert results["liveness"] is True
    assert results["readiness"] is True
    assert results["version"] == "1.1.0"

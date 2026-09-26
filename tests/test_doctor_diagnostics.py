"""
Unit tests for the enhanced diagnostic tool (scripts/doctor.py).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add root to sys.path to allow importing scripts.doctor
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import scripts.doctor as doctor  # noqa: E402


class TestDoctorDiagnostics(unittest.TestCase):
    """Verify diagnostic checks in scripts/doctor.py."""

    def test_check_python_version(self):
        """Verify python version check logic."""
        res = doctor.check_python_version()
        self.assertEqual(res.name, "Python Version")
        if sys.version_info.major == 3 and sys.version_info.minor >= 10:
            self.assertEqual(res.status, "OK")
        else:
            self.assertEqual(res.status, "FAILED")

    def test_check_dependencies_success(self):
        """Verify dependency check passes when all modules exist."""
        with patch("builtins.__import__", return_value=None):
            res = doctor.check_dependencies(dependencies={"Test": "test_mod"})
            self.assertEqual(res.status, "OK")

    def test_check_dependencies_failure(self):
        """Verify dependency check fails when modules are missing."""

        def side_effect(name, *args, **kwargs):
            if name == "non_existent_module":
                raise ImportError(f"No module named '{name}'")
            return None

        with patch("builtins.__import__", side_effect=side_effect):
            res = doctor.check_dependencies(dependencies={"Display": "non_existent_module"})
            self.assertEqual(res.status, "FAILED")
            self.assertIn("Display", res.message)

    def test_check_env_file_missing(self):
        """Verify .env check fails when file is missing."""
        with patch("scripts.doctor.Path.exists", return_value=False):
            res = doctor.check_env_file()
            self.assertEqual(res.status, "FAILED")
            self.assertIn(".env is missing", res.message)

    def test_check_env_file_placeholders(self):
        """Verify .env check warns about placeholders."""
        mock_content = "MT5_PASSWORD=YOUR_PASSWORD_HERE\nMT5_SERVER=test"
        with (
            patch("scripts.doctor.Path.exists", return_value=True),
            patch(
                "builtins.open",
                MagicMock(
                    return_value=MagicMock(
                        __enter__=MagicMock(
                            return_value=MagicMock(read=MagicMock(return_value=mock_content))
                        )
                    )
                ),
            ),
        ):
            res = doctor.check_env_file()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("YOUR_PASSWORD_HERE", res.message)

    def test_check_talib_linkage_error(self):
        """Verify TA-Lib linkage failure handling."""
        mock_numpy = MagicMock()
        mock_talib = MagicMock()
        mock_talib.SMA.side_effect = Exception("Linkage error")
        with patch.dict("sys.modules", {"numpy": mock_numpy, "talib": mock_talib}):
            res = doctor.check_talib()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("Linkage error", res.message)

    def test_check_file_permissions_linux(self):
        """Verify file permission check on Linux-like systems."""
        if sys.platform == "win32":
            self.skipTest("Linux-specific test")

        mock_stat = MagicMock()
        mock_stat.st_mode = 0o666  # Insecure

        with (
            patch("scripts.doctor.Path.exists", return_value=True),
            patch("scripts.doctor.os.stat", return_value=mock_stat),
        ):
            res = doctor.check_file_permissions()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("Insecure", res.message)

    def test_check_mt5_config_incomplete(self):
        """Verify MT5 config check detects missing fields."""
        with patch(
            "scripts.doctor.os.getenv",
            side_effect=lambda k, d=None: "0" if k == "MT5_LOGIN" else "",
        ):
            res = doctor.check_mt5_config()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("Incomplete MT5 configuration", res.message)

    def test_check_git_config_success(self):
        """Verify Git config check passes when user info is set."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="Test User\n"),
                MagicMock(stdout="test@example.com\n"),
            ]
            res = doctor.check_git_config()
            self.assertEqual(res.status, "OK")
            self.assertIn("Test User", res.message)

    def test_check_git_config_missing(self):
        """Verify Git config check warns when info is missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="\n"),
                MagicMock(stdout="\n"),
            ]
            res = doctor.check_git_config()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("user.name or user.email not set", res.message)

    def test_check_branch_naming_valid(self):
        """Verify branch naming check passes for valid prefixes."""
        valid_branches = [
            "feature/test-branch",
            "bugfix/some-fix",
            "hotfix/emergency",
            "docs/update-guide",
            "refactor/optimize",
            "chore/deps",
            "test/add-tests",
            "ci/fix-pipeline",
            "perf/speedup",
            "style/format",
        ]
        for branch_name in valid_branches:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout=f"{branch_name}\n")
                res = doctor.check_branch_naming()
                self.assertEqual(res.status, "OK", f"Expected {branch_name} to be valid")
                self.assertIn("Valid prefix", res.message)

    def test_check_branch_naming_invalid(self):
        """Verify branch naming check warns for invalid prefixes."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="invalid-branch\n")
            res = doctor.check_branch_naming()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("Invalid prefix", res.message)

    def test_check_graft_alignment_aligned(self):
        """Verify graft alignment check passes when aligned."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="common-commit-hash\n")
            res = doctor.check_graft_alignment()
            self.assertEqual(res.status, "OK")
            self.assertIn("Common ancestry found", res.message)

    def test_check_graft_alignment_stale(self):
        """Verify graft alignment check warns when stale."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="\n")
            res = doctor.check_graft_alignment()
            self.assertEqual(res.status, "WARNING")
            self.assertIn("No common ancestry", res.message)

    def test_check_venv_active(self):
        """Verify venv check passes when active."""
        with patch("sys.prefix", "/path/to/venv"), patch("sys.base_prefix", "/usr"):
            res = doctor.check_venv()
            self.assertEqual(res.status, "OK")

    def test_check_venv_inactive(self):
        """Verify venv check warns when inactive."""
        with (
            patch("sys.prefix", "/usr"),
            patch("sys.base_prefix", "/usr"),
            patch("sys.real_prefix", create=True),
            patch(
                "scripts.doctor.hasattr",
                side_effect=lambda obj, attr: False
                if attr == "real_prefix"
                else hasattr(obj, attr),
            ),
        ):
            res = doctor.check_venv()
            self.assertEqual(res.status, "WARNING")

    def test_check_disk_space_ok(self):
        """Verify disk space check passes when sufficient."""
        with patch("shutil.disk_usage", return_value=(100 * (2**30), 10 * (2**30), 10 * (2**30))):
            res = doctor.check_disk_space()
            self.assertEqual(res.status, "OK")

    def test_check_disk_space_failed(self):
        """Verify disk space check fails when critical."""
        with patch(
            "shutil.disk_usage", return_value=(100 * (2**30), 99.9 * (2**30), 0.1 * (2**30))
        ):
            res = doctor.check_disk_space()
            self.assertEqual(res.status, "FAILED")

    def test_get_triage_top_items(self):
        """Verify triage scraping logic."""
        mock_content = """
## 🔝 Top 3 Items That Matter Right Now

1. **Mandatory Rebase:** Rebase required.
2. Item two.
3. Item three.

## Summary Table
"""
        with (
            patch("scripts.doctor.Path.exists", return_value=True),
            patch("scripts.doctor.Path.read_text", return_value=mock_content),
        ):
            items = doctor.get_triage_top_items()
            self.assertEqual(len(items), 3)
            self.assertIn("Mandatory Rebase: Rebase required.", items[0])


if __name__ == "__main__":
    unittest.main()

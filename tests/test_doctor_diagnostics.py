"""
Unit tests for the enhanced diagnostic tool (scripts/doctor.py).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add root to sys.path to allow importing scripts.doctor
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import scripts.doctor as doctor  # noqa: E402  # noqa: E402


def test_check_python_version():
    """Verify python version check logic."""
    res = doctor.check_python_version()
    assert res.name == "Python Version"
    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        assert res.status == "OK"
    else:
        assert res.status == "FAILED"


def test_check_dependencies_success():
    """Verify dependency check passes when all modules exist."""
    with patch("builtins.__import__", return_value=None):
        res = doctor.check_dependencies(dependencies={"Test": "test_mod"})
        assert res.status == "OK"


def test_check_dependencies_failure():
    """Verify dependency check fails when modules are missing."""

    def side_effect(name, *args, **kwargs):
        if name == "non_existent_module":
            raise ImportError(f"No module named '{name}'")
        return None

    with patch("builtins.__import__", side_effect=side_effect):
        res = doctor.check_dependencies(dependencies={"Display": "non_existent_module"})
        assert res.status == "FAILED"
        assert "Display" in res.message


def test_check_env_file_missing():
    """Verify .env check fails when file is missing."""
    with patch("scripts.doctor.Path.exists", return_value=False):
        res = doctor.check_env_file()
        assert res.status == "FAILED"
        assert ".env is missing" in res.message


def test_check_env_file_placeholders():
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
        assert res.status == "WARNING"
        assert "YOUR_PASSWORD_HERE" in res.message


def test_check_talib_linkage_error():
    """Verify TA-Lib linkage failure handling."""
    with patch("talib.SMA", side_effect=Exception("Linkage error")):
        res = doctor.check_talib()
        assert res.status == "WARNING"
        assert "Linkage error" in res.message


def test_check_file_permissions_linux():
    """Verify file permission check on Linux-like systems."""
    if sys.platform == "win32":
        pytest.skip("Linux-specific test")

    # Mock os.stat to return insecure permissions
    mock_stat = MagicMock()
    mock_stat.st_mode = 0o666  # Insecure

    with (
        patch("scripts.doctor.Path.exists", return_value=True),
        patch("scripts.doctor.os.stat", return_value=mock_stat),
    ):
        res = doctor.check_file_permissions()
        assert res.status == "WARNING"
        assert "Insecure" in res.message


def test_check_mt5_config_incomplete():
    """Verify MT5 config check detects missing fields."""
    with patch(
        "scripts.doctor.os.getenv", side_effect=lambda k, d=None: "0" if k == "MT5_LOGIN" else ""
    ):
        res = doctor.check_mt5_config()
        assert res.status == "WARNING"
        assert "Incomplete MT5 configuration" in res.message

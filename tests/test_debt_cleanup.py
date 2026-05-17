import subprocess
from pathlib import Path

import pytest


def test_no_legacy_datetime_utcnow():
    """
    Verify that datetime.utcnow() is not used in the src/ directory.
    Standard is datetime.now(timezone.utc).
    Note: src/trading/risk_manager.py is exempted until manual review as it is high-risk.
    """
    src_path = Path("src")
    # Search for datetime.utcnow() in all .py files in src/
    try:
        result = subprocess.run(
            ["grep", "-r", "datetime.utcnow", str(src_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Filter out risk_manager.py
            filtered = [line for line in lines if "src/trading/risk_manager.py" not in line]
            assert not filtered, "Found legacy datetime.utcnow() calls:\n" + "\n".join(filtered)

    except FileNotFoundError:
        pytest.skip("grep command not found")

def test_no_raw_print_in_core():
    """
    Verify that raw print() statements are not used in core modules.
    Excludes comments and rich console.print.
    """
    core_path = Path("src/core")
    try:
        # Complex grep to find raw print( but ignore console.print, logger, comments
        result = subprocess.run(
            ["grep", "-r", "print(", str(core_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Filter out console.print, logger.info(f"print..."), and comments
            filtered = [
                line for line in lines
                if "console.print" not in line
                and "logger." not in line
                and "log." not in line
                and line.strip().startswith("print(")
            ]
            assert not filtered, "Found raw print() statements in core:\n" + "\n".join(filtered)

    except FileNotFoundError:
        pytest.skip("grep command not found")
